"""
Semantic embeddings for page similarity using sentence-transformers
"""
try:
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    EMBEDDINGS_AVAILABLE = True
except Exception as e:
    print(f"⚠️  Warning: Sentence transformers not available: {e}")
    print("   Continuing without semantic similarity features...")
    EMBEDDINGS_AVAILABLE = False
    import numpy as np

# Global model instance (lazy loaded)
_model = None

def get_embedding_model():
    """Load and cache the sentence transformer model"""
    global _model
    if not EMBEDDINGS_AVAILABLE:
        return None
    if _model is None:
        # Using a lightweight, fast model optimized for semantic similarity
        _model = SentenceTransformer('all-MiniLM-L6-v2')
    return _model


def generate_embeddings(texts):
    """
    Generate embeddings for a list of text strings.
    
    Args:
        texts: List of strings to encode
        
    Returns:
        numpy array of embeddings, shape (len(texts), embedding_dim)
    """
    if not EMBEDDINGS_AVAILABLE:
        # Return dummy embeddings (zeros) if model not available
        return np.zeros((len(texts), 384))
    
    model = get_embedding_model()
    if model is None:
        return np.zeros((len(texts), 384))
    
    # Clean texts (handle empty strings)
    clean_texts = [text if text.strip() else " " for text in texts]
    
    embeddings = model.encode(clean_texts, show_progress_bar=False)
    return np.array(embeddings)


def compute_similarity(embedding1, embedding2):
    """
    Compute cosine similarity between two embeddings.
    
    Args:
        embedding1: First embedding vector
        embedding2: Second embedding vector
        
    Returns:
        Similarity score between 0 and 1
    """
    if not EMBEDDINGS_AVAILABLE:
        return 0.0
    
    # Reshape for sklearn
    emb1 = np.array(embedding1).reshape(1, -1)
    emb2 = np.array(embedding2).reshape(1, -1)
    
    similarity = cosine_similarity(emb1, emb2)[0][0]
    return float(similarity)


def compute_similarity_matrix(embeddings):
    """
    Compute pairwise similarity matrix for all embeddings.
    
    Args:
        embeddings: numpy array of embeddings
        
    Returns:
        Similarity matrix (n x n)
    """
    return cosine_similarity(embeddings)


def find_similar_pages(target_embedding, all_embeddings, threshold=0.95):
    """
    Find pages similar to the target page.
    
    Args:
        target_embedding: Embedding of the target page
        all_embeddings: Array of all page embeddings
        threshold: Similarity threshold (default 0.95 for near-duplicates)
        
    Returns:
        List of indices of similar pages
    """
    target = np.array(target_embedding).reshape(1, -1)
    similarities = cosine_similarity(target, all_embeddings)[0]
    
    # Find indices where similarity exceeds threshold (excluding self)
    similar_indices = np.where(similarities >= threshold)[0]
    
    return similar_indices.tolist()


def compute_continuity_scores(embeddings):
    """
    Compute continuity scores between consecutive pages.
    Higher score = better semantic flow.
    
    Args:
        embeddings: Array of page embeddings in current order
        
    Returns:
        List of continuity scores (length = n-1)
    """
    if len(embeddings) < 2:
        return []
    
    scores = []
    for i in range(len(embeddings) - 1):
        similarity = compute_similarity(embeddings[i], embeddings[i + 1])
        scores.append(similarity)
    
    return scores
