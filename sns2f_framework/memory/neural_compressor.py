# sns2f_framework/memory/neural_compressor.py

import logging
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List
import os

# We must import our config to get the model name and dimension
from sns2f_framework.config import EMBEDDING_MODEL_NAME, EMBEDDING_DIMENSION

# Set up logging for this module
log = logging.getLogger(__name__)

class NeuralCompressor:
    """
    A CPU-friendly wrapper for creating latent representations (embeddings)
    from text using a lightweight sentence-transformer model.
    
    This class abstracts the underlying embedding model from the rest of the
    memory and reasoning systems. If we ever want to change the model,
    we only need to update this file and the config.
    """
    
    def __init__(self, model_name: str = EMBEDDING_MODEL_NAME, 
                 dimension: int = EMBEDDING_DIMENSION):
        """
        Initializes the compressor and loads the model into memory.
        
        This operation may take a few seconds as the model is
        downloaded (on first run) and loaded.
        """
        self.model_name = model_name
        self._dimension = dimension
        self.model: SentenceTransformer = None

        try:
            # Suppress the "no sentence-transformers model found" warning 
            # if it's downloading for the first time.
            logging.getLogger('sentence_transformers').setLevel(logging.WARNING)
            
            log.info(f"Loading neural compressor model: {self.model_name}...")
            # This will download the model from Hugging Face if not present
            # in the cache and then load it.
            self.model = SentenceTransformer(self.model_name)
            log.info(f"Model {self.model_name} loaded successfully.")
            
            # --- Model Verification ---
            # It's good practice to verify the model's output dimension
            # matches what our config expects.
            actual_dim = self.model.get_sentence_embedding_dimension()
            if actual_dim != self._dimension:
                log.warning(
                    f"Model dimension mismatch! Config specified {self._dimension}, "
                    f"but model '{self.model_name}' has dimension {actual_dim}. "
                    f"Using model's actual dimension: {actual_dim}"
                )
                self._dimension = actual_dim
                
        except Exception as e:
            log.critical(f"Failed to load sentence-transformer model '{self.model_name}'. {e}", exc_info=True)
            log.critical("The NeuralCompressor is non-functional. The system will likely fail.")
            # In a production system, we might have a fallback or a retry.
            # For this build, we'll raise it so the developer knows.
            raise RuntimeError(f"Could not initialize NeuralCompressor: {e}")

    def embed(self, text: str) -> np.ndarray:
        """
        Compresses a single string of text into a neural embedding.

        Args:
            text: The raw text string (e.g., a sentence, a paragraph).

        Returns:
            A 1D numpy array representing the text in latent space.
        """
        if not self.model:
            log.error("Model is not loaded. Cannot embed. Returning zero vector.")
            return np.zeros(self._dimension, dtype=np.float32)
            
        try:
            # normalize_embeddings=True converts the output vector to unit length (magnitude 1).
            # This is crucial for efficient similarity search, as cosine similarity
            # between two normalized vectors is simply their dot product.
            embedding = self.model.encode(
                text, 
                convert_to_numpy=True, 
                normalize_embeddings=True
            )
            # We cast to float32 to save space. float64 is overkill.
            return embedding.astype(np.float32)
        except Exception as e:
            log.error(f"Error during embedding of text: '{text[:50]}...': {e}", exc_info=True)
            return np.zeros(self._dimension, dtype=np.float32)

    def embed_batch(self, texts: List[str]) -> List[np.ndarray]:
        """
        Compresses a batch of text strings into neural embeddings.
        This is significantly more-efficient than calling embed() in a loop.

        Args:
            texts: A list of raw text strings.

        Returns:
            A list of 1D numpy arrays.
        """
        if not self.model:
            log.error("Model is not loaded. Cannot embed batch. Returning zero vectors.")
            return [np.zeros(self._dimension, dtype=np.float32) for _ in texts]
        
        try:
            embeddings = self.model.encode(
                texts, 
                convert_to_numpy=True, 
                normalize_embeddings=True
            )
            return [emb.astype(np.float32) for emb in embeddings]
        except Exception as e:
            log.error(f"Error during batch embedding: {e}", exc_info=True)
            return [np.zeros(self._dimension, dtype=np.float32) for _ in texts]

    @property
    def dimension(self) -> int:
        """Returns the output dimension of the embeddings."""
        return self._dimension

# --- Self-Test Execution ---
if __name__ == "__main__":
    """
    This block allows for direct, local testing of this module.
    You can run this file directly: python sns2f_framework/memory/neural_compressor.py
    
    It requires the 'sns2f_framework/config.py' file to be present.
    """
    
    # --- Configure basic logging for testing ---
    # This setup ensures you see the log output from this module
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        # We need to set up a basic handler
        handlers=[logging.StreamHandler()]
    )
    
    # Create a dummy config.py if it doesn't exist, just for this test
    if not os.path.exists('config.py'):
        print("Creating dummy config.py for testing...")
        with open('config.py', 'w') as f:
            f.write("import os\n")
            f.write("EMBEDDING_MODEL_NAME = 'all-MiniLM-L6-v2'\n")
            f.write("EMBEDDING_DIMENSION = 384\n")
            f.write("BASE_DIR = os.path.dirname(os.path.abspath(__file__))\n")
            f.write("DATA_DIR = os.path.join(BASE_DIR, 'data')\n")
            f.write("DB_PATH = os.path.join(DATA_DIR, 'sns2f_memory.sqlite')\n")
            f.write("LOG_PATH = os.path.join(DATA_DIR, 'logs', 'system.log')\n")
            f.write("CHECKPOINT_DIR = os.path.join(DATA_DIR, 'checkpoints')\n")
            f.write("WHITELISTED_SOURCES = []\n")
            f.write("STM_CAPACITY = 100\n")
            f.write("AGENT_SLEEP_INTERVAL = 0.1\n")

    log.info("--- [Test] Testing NeuralCompressor ---")
    
    try:
        # 1. Initialization
        log.info("Instantiating NeuralCompressor...")
        compressor = NeuralCompressor()
        
        log.info(f"Compressor loaded. Model: {compressor.model_name}, Dimension: {compressor.dimension}")
        assert compressor.dimension == 384, "Dimension should be 384"
        
        # 2. Test Single Embedding
        text1 = "This is a test of the Self-Evolving Neuro-Symbolic Swarm Framework."
        log.info(f"Embedding single text: '{text1}'")
        embedding1 = compressor.embed(text1)
        
        log.info(f"  -> Result type: {type(embedding1)}")
        log.info(f"  -> Result shape: {embedding1.shape}")
        log.info(f"  -> Result dtype: {embedding1.dtype}")
        
        assert embedding1.shape == (compressor.dimension,), "Shape mismatch"
        assert embedding1.dtype == np.float32, "Dtype mismatch"
        
        # 3. Test Batch Embedding
        texts_batch = [
            "What is sparse activation?",
            "How does symbolic reasoning work?",
            "This is the third sentence."
        ]
        log.info(f"Embedding batch of {len(texts_batch)} texts...")
        embeddings_batch = compressor.embed_batch(texts_batch)
        
        log.info(f"  -> Result type: {type(embeddings_batch)}")
        log.info(f"  -> Result count: {len(embeddings_batch)}")
        log.info(f"  -> First item shape: {embeddings_batch[0].shape}")
        
        assert len(embeddings_batch) == 3, "Batch count mismatch"
        assert embeddings_batch[0].shape == (compressor.dimension,), "Batch shape mismatch"

        log.info("--- [Test] NeuralCompressor Test Passed ---")
        
    except Exception as e:
        log.error(f"[Test] Test failed: {e}", exc_info=True)
    
    finally:
        # Clean up the dummy config if we created it
        if 'f' in locals() and not f.closed:
            f.close()
        if os.path.exists('config.py') and 'dummy' in open('config.py').read():
            print("Cleaning up dummy config.py...")
            os.remove('config.py')