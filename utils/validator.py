# utils/validator.py - Feature 2: Bid-to-Requirement Validator
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from typing import List, Dict, Tuple
import re

class BidValidator:
    def __init__(self):
        # Load pre-trained sentence transformer model
        # This model is specifically good for semantic similarity
        try:
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
        except:
            # Fallback to simpler approach if model download fails
            self.model = None
        
        self.similarity_threshold = 0.65  # Minimum similarity to consider a match
        self.high_confidence_threshold = 0.80
    
    def validate_proposal(self, requirements: List[Dict], proposal_text: str) -> List[Dict]:
        """
        Validate vendor proposal against extracted requirements
        Returns requirements with validation results
        """
        # Segment proposal into sentences/paragraphs
        proposal_segments = self._segment_proposal(proposal_text)
        
        validated_requirements = []
        
        for req in requirements:
            # Find best matching segment in proposal
            match_result = self._find_best_match(req['text'], proposal_segments)
            
            req['matched_proposal_text'] = match_result['matched_text']
            # Convert numpy floats to Python floats for database compatibility
            req['match_confidence'] = float(match_result['confidence'])
            req['similarity_score'] = float(match_result['similarity'])
            req['validation_status'] = self._determine_validation_status(match_result)
            req['alternative_matches'] = match_result.get('alternatives', [])
            
            validated_requirements.append(req)
        
        return validated_requirements
    
    def _segment_proposal(self, text: str) -> List[str]:
        """Segment proposal into meaningful chunks"""
        # Split by paragraphs first
        paragraphs = [p.strip() for p in text.split('\n\n') if len(p.strip()) > 30]
        
        # If paragraph is too long, split into sentences
        segments = []
        for para in paragraphs:
            if len(para) > 500:
                sentences = re.split(r'(?<=[.!?])\s+', para)
                segments.extend([s.strip() for s in sentences if len(s.strip()) > 20])
            else:
                segments.append(para)
        
        return segments
    
    def _find_best_match(self, requirement: str, proposal_segments: List[str]) -> Dict:
        """Find the best matching text segment for a requirement"""
        if not self.model or not proposal_segments:
            # Fallback to keyword matching
            return self._keyword_match(requirement, proposal_segments)
        
        # Generate embeddings
        req_embedding = self.model.encode([requirement])
        segment_embeddings = self.model.encode(proposal_segments)
        
        # Calculate cosine similarities
        similarities = cosine_similarity(req_embedding, segment_embeddings)[0]
        
        # Get best match
        best_idx = np.argmax(similarities)
        best_similarity = similarities[best_idx]
        
        # Get top 3 alternatives for context
        top_indices = np.argsort(similarities)[-3:][::-1]
        alternatives = [
            {
                'text': proposal_segments[idx][:200] + "..." if len(proposal_segments[idx]) > 200 else proposal_segments[idx],
                'score': float(similarities[idx])
            }
            for idx in top_indices if idx != best_idx and similarities[idx] > 0.3
        ]
        
        # Calculate confidence based on similarity
        confidence = self._calculate_confidence(best_similarity, requirement, proposal_segments[best_idx])
        
        return {
            'matched_text': proposal_segments[best_idx],
            'similarity': float(best_similarity),
            'confidence': confidence,
            'alternatives': alternatives[:2]  # Top 2 alternatives
        }
    
    def _calculate_confidence(self, similarity: float, req_text: str, matched_text: str) -> float:
        """Calculate confidence score based on multiple factors"""
        base_confidence = float(similarity)
        
        # Boost confidence for high similarity
        if similarity > self.high_confidence_threshold:
            base_confidence += 0.1
        
        # Check for specific commitment language in match
        commitment_words = ['will', 'shall', 'commit', 'guarantee', 'provide', 'ensure', 'confirm']
        matched_lower = matched_text.lower()
        
        commitment_score = sum(1 for word in commitment_words if word in matched_lower) * 0.02
        
        # Penalize vague language
        vague_words = ['may', 'might', 'could', 'possibly', 'consider', 'try', 'attempt']
        vague_penalty = sum(1 for word in vague_words if word in matched_lower) * 0.03
        
        final_confidence = base_confidence + commitment_score - vague_penalty
        return float(min(1.0, max(0.0, final_confidence)))
    
    def _determine_validation_status(self, match_result: Dict) -> str:
        confidence = match_result['confidence']
        similarity = match_result['similarity']

        if confidence >= self.high_confidence_threshold and similarity > 0.75:
            return "Fully Addressed"
        elif confidence >= self.similarity_threshold:
            return "Partially Addressed"
        elif similarity > 0.4:
            return "Insufficiently Addressed"
        else:
            return "Missing"
    
    def _keyword_match(self, requirement: str, segments: List[str]) -> Dict:
        """Fallback keyword-based matching"""
        req_words = set(requirement.lower().split())
        best_score = 0
        best_segment = ""
        
        for segment in segments:
            seg_words = set(segment.lower().split())
            intersection = req_words & seg_words
            union = req_words | seg_words
            score = len(intersection) / len(union) if union else 0
            
            if score > best_score:
                best_score = score
                best_segment = segment
        
        confidence = self._calculate_confidence(best_score, requirement, best_segment)
        
        return {
            'matched_text': best_segment if best_segment else "No match found",
            'similarity': best_score,
            'confidence': confidence,
            'alternatives': []
        }