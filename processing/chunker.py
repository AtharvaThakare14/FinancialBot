"""
Intelligent text chunker for loan product content.

This module implements semantic chunking strategy optimized for loan information.
Chunks are created to preserve complete information units while staying within
token limits for embedding and retrieval.

Chunking Strategy:
- Size: 450 tokens (~300-350 words)
- Overlap: 50 tokens to maintain context
- Semantic boundaries: Preserve sections, paragraphs, lists
- Metadata: Track source, loan type, section
"""

import re
from typing import List, Dict, Tuple
from dataclasses import dataclass
import tiktoken
import logging

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """
    Represents a text chunk with metadata.
    
    Attributes:
        text: The chunk content
        metadata: Dictionary containing source information
        token_count: Number of tokens in the chunk
        chunk_id: Unique identifier for the chunk
    """
    text: str
    metadata: Dict[str, str]
    token_count: int
    chunk_id: str


class LoanContentChunker:
    """
    Intelligent chunker for loan product content.
    
    Uses semantic boundaries to create meaningful chunks that:
    1. Stay within token limits
    2. Preserve complete information units
    3. Maintain context through overlap
    4. Include rich metadata for retrieval
    """
    
    def __init__(
        self,
        chunk_size: int = 450,
        chunk_overlap: int = 50,
        encoding_name: str = "cl100k_base"  # GPT-4 tokenizer
    ):
        """
        Initialize the chunker.
        
        Args:
            chunk_size: Target tokens per chunk
            chunk_overlap: Overlap tokens between chunks
            encoding_name: Tokenizer to use
        
        Why these defaults?
        - 450 tokens: Enough for complete loan product info (rates, eligibility, etc.)
        - 50 token overlap: Prevents information loss at boundaries
        - cl100k_base: Compatible with modern LLMs
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        try:
            self.tokenizer = tiktoken.get_encoding(encoding_name)
        except Exception as e:
            logger.warning(f"Failed to load {encoding_name}, using default: {e}")
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
    
    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text.
        
        Args:
            text: Text to count
        
        Returns:
            Number of tokens
        """
        return len(self.tokenizer.encode(text))
    
    def split_by_semantic_boundaries(self, text: str) -> List[str]:
        """
        Split text by semantic boundaries (sections, paragraphs).
        
        This preserves the logical structure of loan information.
        
        Args:
            text: Text to split
        
        Returns:
            List of text segments
        """
        # First, try to split by major sections (double newlines)
        sections = re.split(r'\n\n+', text)
        
        segments = []
        for section in sections:
            section = section.strip()
            if not section:
                continue
            
            # If section is too long, split by sentences
            if self.count_tokens(section) > self.chunk_size:
                sentences = re.split(r'(?<=[.!?])\s+', section)
                segments.extend(sentences)
            else:
                segments.append(section)
        
        return segments
    
    def create_chunks(
        self,
        text: str,
        metadata: Dict[str, str]
    ) -> List[Chunk]:
        """
        Create overlapping chunks from text.
        
        Algorithm:
        1. Split text by semantic boundaries
        2. Combine segments until chunk_size is reached
        3. Add overlap from previous chunk
        4. Attach metadata to each chunk
        
        Args:
            text: Text to chunk
            metadata: Metadata to attach (loan_type, url, etc.)
        
        Returns:
            List of Chunk objects
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for chunking")
            return []
        
        # Split by semantic boundaries
        segments = self.split_by_semantic_boundaries(text)
        
        chunks = []
        current_chunk = []
        current_tokens = 0
        chunk_counter = 0
        
        for i, segment in enumerate(segments):
            segment_tokens = self.count_tokens(segment)
            
            # If single segment exceeds chunk_size, split it forcefully
            if segment_tokens > self.chunk_size:
                # Save current chunk if exists
                if current_chunk:
                    chunks.append(self._create_chunk(
                        current_chunk, metadata, chunk_counter
                    ))
                    chunk_counter += 1
                    current_chunk = []
                    current_tokens = 0
                
                # Split long segment by tokens
                tokens = self.tokenizer.encode(segment)
                for j in range(0, len(tokens), self.chunk_size - self.chunk_overlap):
                    chunk_tokens = tokens[j:j + self.chunk_size]
                    chunk_text = self.tokenizer.decode(chunk_tokens)
                    chunks.append(self._create_chunk(
                        [chunk_text], metadata, chunk_counter
                    ))
                    chunk_counter += 1
                
                continue
            
            # Check if adding segment exceeds chunk_size
            if current_tokens + segment_tokens > self.chunk_size:
                # Save current chunk
                chunks.append(self._create_chunk(
                    current_chunk, metadata, chunk_counter
                ))
                chunk_counter += 1
                
                # Start new chunk with overlap
                overlap_text = self._get_overlap_text(current_chunk)
                current_chunk = [overlap_text, segment] if overlap_text else [segment]
                current_tokens = self.count_tokens(' '.join(current_chunk))
            else:
                # Add segment to current chunk
                current_chunk.append(segment)
                current_tokens += segment_tokens
        
        # Add final chunk
        if current_chunk:
            chunks.append(self._create_chunk(
                current_chunk, metadata, chunk_counter
            ))
        
        logger.info(
            f"Created {len(chunks)} chunks from {self.count_tokens(text)} tokens "
            f"(avg {sum(c.token_count for c in chunks) / len(chunks):.0f} tokens/chunk)"
        )
        
        return chunks
    
    def _get_overlap_text(self, chunk_segments: List[str]) -> str:
        """
        Get overlap text from previous chunk.
        
        Args:
            chunk_segments: Segments from previous chunk
        
        Returns:
            Text for overlap (last ~50 tokens)
        """
        if not chunk_segments:
            return ""
        
        # Get last segments until we have ~overlap tokens
        full_text = ' '.join(chunk_segments)
        tokens = self.tokenizer.encode(full_text)
        
        if len(tokens) <= self.chunk_overlap:
            return full_text
        
        overlap_tokens = tokens[-self.chunk_overlap:]
        return self.tokenizer.decode(overlap_tokens)
    
    def _create_chunk(
        self,
        segments: List[str],
        metadata: Dict[str, str],
        chunk_id: int
    ) -> Chunk:
        """
        Create a Chunk object from segments.
        
        Args:
            segments: Text segments to combine
            metadata: Metadata dictionary
            chunk_id: Chunk identifier
        
        Returns:
            Chunk object
        """
        text = ' '.join(segments).strip()
        token_count = self.count_tokens(text)
        
        # Enhance metadata with chunk info
        chunk_metadata = {
            **metadata,
            'chunk_id': f"{metadata.get('loan_type', 'unknown')}_{chunk_id}",
            'chunk_index': str(chunk_id),
            'token_count': str(token_count),
        }
        
        return Chunk(
            text=text,
            metadata=chunk_metadata,
            token_count=token_count,
            chunk_id=chunk_metadata['chunk_id']
        )
    
    def chunk_loan_data(self, cleaned_data: Dict) -> List[Chunk]:
        """
        Chunk cleaned loan data.
        
        Args:
            cleaned_data: Cleaned data dictionary from cleaner
        
        Returns:
            List of chunks
        """
        loan_type = cleaned_data.get('loan_type', 'unknown')
        logger.info(f"Chunking {loan_type} data")
        
        # Base metadata
        metadata = {
            'loan_type': loan_type,
            'url': cleaned_data.get('url', ''),
            'title': cleaned_data.get('title', ''),
        }
        
        all_chunks = []
        
        # Chunk main content
        main_text = cleaned_data.get('cleaned_text', '')
        if main_text:
            chunks = self.create_chunks(main_text, metadata)
            all_chunks.extend(chunks)
        
        # Also chunk individual sections with section metadata
        sections = cleaned_data.get('sections', {})
        for section_name, section_text in sections.items():
            if section_text:
                section_metadata = {
                    **metadata,
                    'section': section_name
                }
                chunks = self.create_chunks(section_text, section_metadata)
                all_chunks.extend(chunks)
        
        logger.info(f"Created {len(all_chunks)} total chunks for {loan_type}")
        return all_chunks
    
    def chunk_all_loans(self, cleaned_data_list: List[Dict]) -> List[Chunk]:
        """
        Chunk all loan data.
        
        Args:
            cleaned_data_list: List of cleaned data dictionaries
        
        Returns:
            List of all chunks
        """
        all_chunks = []
        
        for cleaned_data in cleaned_data_list:
            chunks = self.chunk_loan_data(cleaned_data)
            all_chunks.extend(chunks)
        
        logger.info(f"Total chunks created: {len(all_chunks)}")
        
        # Log statistics
        if all_chunks:
            token_counts = [c.token_count for c in all_chunks]
            logger.info(
                f"Chunk statistics: "
                f"min={min(token_counts)}, "
                f"max={max(token_counts)}, "
                f"avg={sum(token_counts)/len(token_counts):.0f}"
            )
        
        return all_chunks


def main():
    """Main function to test chunker."""
    import json
    from pathlib import Path
    
    # Load cleaned data
    cleaned_file = Path('data/processed/all_loans_cleaned.json')
    if not cleaned_file.exists():
        print("Error: Run cleaner.py first to generate cleaned data")
        return
    
    with open(cleaned_file, 'r', encoding='utf-8') as f:
        cleaned_data_list = json.load(f)
    
    # Create chunks
    chunker = LoanContentChunker()
    chunks = chunker.chunk_all_loans(cleaned_data_list)
    
    # Save chunks
    output_file = Path('data/processed/chunks.json')
    chunks_data = [
        {
            'text': chunk.text,
            'metadata': chunk.metadata,
            'token_count': chunk.token_count,
            'chunk_id': chunk.chunk_id
        }
        for chunk in chunks
    ]
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(chunks_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Created {len(chunks)} chunks")
    print(f"✓ Saved to {output_file}")
    
    # Print sample
    if chunks:
        print(f"\nSample chunk:")
        print(f"  ID: {chunks[0].chunk_id}")
        print(f"  Tokens: {chunks[0].token_count}")
        print(f"  Text preview: {chunks[0].text[:200]}...")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
