# skillswap2/app/ml/vectorizer.py
"""
Skill Vectorization Module
Phase 6: Convert skill descriptions to numerical vectors for similarity computation
"""

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Tuple, Optional
import pickle
import os


class SkillVectorizer:
    """
    Vectorizes skill descriptions using TF-IDF.
    Supports training, saving, and loading of vectorizer.
    """
    
    def __init__(self):
        """Initialize TF-IDF vectorizer with optimized parameters"""
        self.vectorizer = TfidfVectorizer(
            max_features=500,           # Limit vocabulary size
            ngram_range=(1, 2),         # Use unigrams and bigrams
            stop_words='english',       # Remove common English words
            min_df=1,                   # Minimum document frequency
            max_df=0.8,                 # Maximum document frequency (ignore very common terms)
            lowercase=True,
            strip_accents='unicode'
        )
        self.is_fitted = False
        
    def fit(self, skill_descriptions: List[str]):
        """
        Fit the vectorizer on skill descriptions.
        
        Args:
            skill_descriptions: List of skill description strings
        """
        if not skill_descriptions or len(skill_descriptions) == 0:
            raise ValueError("Cannot fit on empty skill descriptions")
        
        # Clean and validate descriptions
        cleaned_descriptions = self._clean_descriptions(skill_descriptions)
        
        # Fit vectorizer
        self.vectorizer.fit(cleaned_descriptions)
        self.is_fitted = True
        
    def transform(self, skill_descriptions: List[str]) -> np.ndarray:
        """
        Transform skill descriptions to TF-IDF vectors.
        
        Args:
            skill_descriptions: List of skill description strings
            
        Returns:
            numpy array of TF-IDF vectors (n_samples, n_features)
            
        Raises:
            ValueError: If vectorizer not fitted
        """
        if not self.is_fitted:
            raise ValueError("Vectorizer must be fitted before transform. Call fit() first.")
        
        if not skill_descriptions or len(skill_descriptions) == 0:
            return np.array([])
        
        cleaned_descriptions = self._clean_descriptions(skill_descriptions)
        return self.vectorizer.transform(cleaned_descriptions).toarray()
    
    def fit_transform(self, skill_descriptions: List[str]) -> np.ndarray:
        """
        Fit vectorizer and transform descriptions in one step.
        
        Args:
            skill_descriptions: List of skill description strings
            
        Returns:
            numpy array of TF-IDF vectors
        """
        self.fit(skill_descriptions)
        return self.transform(skill_descriptions)
    
    def compute_similarity(
        self,
        learner_vectors: np.ndarray,
        mentor_vectors: np.ndarray
    ) -> np.ndarray:
        """
        Compute cosine similarity between learner and mentor skill vectors.
        
        Args:
            learner_vectors: Learner skill vectors (n_learners, n_features)
            mentor_vectors: Mentor skill vectors (n_mentors, n_features)
            
        Returns:
            Similarity matrix (n_learners, n_mentors) with values in [0, 1]
        """
        if learner_vectors.size == 0 or mentor_vectors.size == 0:
            return np.array([])
        
        # Compute cosine similarity
        similarities = cosine_similarity(learner_vectors, mentor_vectors)
        
        # Clip to [0, 1] range (cosine similarity can be [-1, 1])
        similarities = np.clip(similarities, 0, 1)
        
        return similarities
    
    def _clean_descriptions(self, descriptions: List[str]) -> List[str]:
        """
        Clean and validate skill descriptions.
        
        Args:
            descriptions: List of skill description strings
            
        Returns:
            List of cleaned descriptions
        """
        cleaned = []
        for desc in descriptions:
            if desc is None or not isinstance(desc, str):
                cleaned.append("")
            else:
                # Remove extra whitespace and convert to string
                cleaned_desc = " ".join(str(desc).split())
                cleaned.append(cleaned_desc if cleaned_desc else "unknown skill")
        
        return cleaned
    
    def save(self, filepath: str):
        """
        Save fitted vectorizer to disk.
        
        Args:
            filepath: Path to save the vectorizer
        """
        if not self.is_fitted:
            raise ValueError("Cannot save unfitted vectorizer")
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'wb') as f:
            pickle.dump(self.vectorizer, f)
    
    @classmethod
    def load(cls, filepath: str) -> 'SkillVectorizer':
        """
        Load fitted vectorizer from disk.
        
        Args:
            filepath: Path to load the vectorizer from
            
        Returns:
            Loaded SkillVectorizer instance
        """
        instance = cls()
        
        with open(filepath, 'rb') as f:
            instance.vectorizer = pickle.load(f)
            instance.is_fitted = True
        
        return instance
    
    def get_feature_names(self) -> List[str]:
        """
        Get feature names (vocabulary) from fitted vectorizer.
        
        Returns:
            List of feature names
        """
        if not self.is_fitted:
            raise ValueError("Vectorizer must be fitted first")
        
        return self.vectorizer.get_feature_names_out().tolist()
    
    def get_vocabulary_size(self) -> int:
        """
        Get size of learned vocabulary.
        
        Returns:
            Number of features in vocabulary
        """
        if not self.is_fitted:
            return 0
        
        return len(self.vectorizer.vocabulary_)


# ======================
# HELPER FUNCTIONS
# ======================

def aggregate_skill_vectors(
    skill_vectors: List[np.ndarray],
    method: str = 'mean'
) -> np.ndarray:
    """
    Aggregate multiple skill vectors into a single vector.
    
    Args:
        skill_vectors: List of skill vectors
        method: Aggregation method ('mean', 'max', 'sum')
        
    Returns:
        Aggregated vector
    """
    if not skill_vectors or len(skill_vectors) == 0:
        return np.array([])
    
    stacked = np.vstack(skill_vectors)
    
    if method == 'mean':
        return np.mean(stacked, axis=0)
    elif method == 'max':
        return np.max(stacked, axis=0)
    elif method == 'sum':
        return np.sum(stacked, axis=0)
    else:
        raise ValueError(f"Unknown aggregation method: {method}")


def normalize_vector(vector: np.ndarray) -> np.ndarray:
    """
    Normalize a vector to unit length.
    
    Args:
        vector: Input vector
        
    Returns:
        Normalized vector
    """
    norm = np.linalg.norm(vector)
    if norm == 0:
        return vector
    return vector / norm