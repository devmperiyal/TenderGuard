# utils/extractor.py - Feature 1: Requirement Extraction Engine
import re
import spacy
from typing import List, Dict, Tuple

class RequirementExtractor:
    def __init__(self):
        # Load spaCy model for NLP processing
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except:
            # Fallback if model not installed
            self.nlp = None
        
        # Mandatory keywords with weights
        self.mandatory_keywords = {
            'shall': 1.0,
            'must': 1.0,
            'required': 0.9,
            'mandatory': 1.0,
            'will': 0.8,
            'should': 0.7,
            'necessary': 0.8,
            'essential': 0.9,
            'critical': 0.9,
            'obligation': 0.9,
            'comply': 0.8,
            'conform': 0.8
        }
        
        # Category detection patterns
        self.category_patterns = {
            'Technical Specifications': [
                r'(?i)(technical|specification|system|software|hardware|architecture|integration|api|performance|scalability|uptime|availability)'
            ],
            'Legal Compliance': [
                r'(?i)(legal|compliance|regulatory|certification|iso|gdpr|hipaa|soc|audit|liability|indemnification|warranty|ip|intellectual property)'
            ],
            'Financial Terms': [
                r'(?i)(financial|payment|price|cost|budget|invoice|pricing|fee|penalty|liquidated damages|warranty bond|performance bond)'
            ],
            'Security & Data': [
                r'(?i)(security|data protection|encryption|access control|authentication|confidentiality|backup|disaster recovery|breach)'
            ],
            'Service Level': [
                r'(?i)(sla|service level|support|maintenance|response time|resolution time|availability|uptime|helpdesk|24/7)'
            ],
            'Qualifications': [
                r'(?i)(experience|qualification|certified|expert|personnel|staff|team|reference|past performance|similar project)'
            ]
        }
    
    def extract_requirements(self, text: str) -> List[Dict]:
        """
        Extract mandatory requirements from RFP text
        Returns list of dicts with requirement details
        """
        requirements = []
        sentences = self._segment_sentences(text)
        
        for idx, sentence in enumerate(sentences):
            # Check for mandatory language
            mandatory_info = self._detect_mandatory_language(sentence)
            
            if mandatory_info['is_mandatory']:
                category = self._categorize_requirement(sentence)
                
                req = {
                    'id': f"REQ-{idx+1:03d}",
                    'text': sentence.strip(),
                    'confidence': mandatory_info['confidence'],
                    'category': category,
                    'keywords_found': mandatory_info['keywords'],
                    'status': 'pending',
                    'matched_proposal_text': None,
                    'match_confidence': 0.0,
                    'validation_status': 'Not Checked'
                }
                requirements.append(req)
        
        return requirements
    
    def _segment_sentences(self, text: str) -> List[str]:
        """Segment text into sentences using spaCy or regex fallback"""
        if self.nlp:
            doc = self.nlp(text)
            return [sent.text for sent in doc.sents]
        else:
            # Fallback regex sentence segmentation
            sentences = re.split(r'(?<=[.!?])\s+', text)
            return [s.strip() for s in sentences if len(s.strip()) > 20]
    
    def _detect_mandatory_language(self, sentence: str) -> Dict:
        """Detect mandatory keywords and calculate confidence"""
        sentence_lower = sentence.lower()
        found_keywords = []
        max_confidence = 0.0
        
        for keyword, weight in self.mandatory_keywords.items():
            if keyword in sentence_lower:
                found_keywords.append(keyword)
                max_confidence = max(max_confidence, weight)
        
        # Boost confidence for multiple keywords
        if len(found_keywords) > 1:
            max_confidence = min(1.0, max_confidence + 0.1)
        
        # Check for negative context (exceptions)
        negative_patterns = ['not required', 'optional', 'if desired', 'preferred but not', 'would be nice']
        is_negative = any(neg in sentence_lower for neg in negative_patterns)
        
        return {
            'is_mandatory': len(found_keywords) > 0 and not is_negative,
            'confidence': max_confidence if not is_negative else 0.0,
            'keywords': found_keywords
        }
    
    def _categorize_requirement(self, sentence: str) -> str:
        """Categorize requirement based on keyword patterns"""
        sentence_lower = sentence.lower()
        category_scores = {}
        
        for category, patterns in self.category_patterns.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, sentence_lower):
                    score += 1
            if score > 0:
                category_scores[category] = score
        
        if category_scores:
            return max(category_scores, key=category_scores.get)
        return "General Requirements"