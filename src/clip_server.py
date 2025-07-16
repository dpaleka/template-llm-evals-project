"""
CLIP embedding server for generating image and text embeddings.
Runs as a separate process to handle the computationally expensive CLIP model.
Supports dynamic batching for improved efficiency.
"""

import argparse
import asyncio
import base64
import io
import logging
from dataclasses import dataclass
from typing import Any

import torch
import uvicorn
from PIL import Image
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from transformers import CLIPModel, CLIPProcessor

LOGGER = logging.getLogger(__name__)


@dataclass
class BatchRequest:
    """Represents a batched request."""

    data: Any
    response_queue: asyncio.Queue
    request_type: str  # 'image' or 'text'


class CLIPEmbeddingServer:
    def __init__(
        self,
        model_name: str = "laion/CLIP-ViT-B-32-laion2B-s34B-b79K",
        max_batch_size: int = 8,
        batch_timeout_ms: int = 2,
    ):
        self.model_name = model_name
        self.max_batch_size = max_batch_size
        self.batch_timeout_ms = batch_timeout_ms
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        LOGGER.info(f"Loading CLIP model {model_name} on {self.device}")

        self.model = CLIPModel.from_pretrained(model_name)
        self.processor = CLIPProcessor.from_pretrained(model_name)
        self.model.to(self.device)
        self.model.eval()

        # Initialize request queue and processing task
        self.request_queue: asyncio.Queue = asyncio.Queue()
        self.processing_task = None

        LOGGER.info(f"CLIP model loaded successfully (batch_size={max_batch_size}, timeout={batch_timeout_ms}ms)")

    def start_processing(self):
        """Start the background processing task."""
        if self.processing_task is None:
            self.processing_task = asyncio.create_task(self._process_batches())
            LOGGER.info("Started batch processing task")

    def stop_processing(self):
        """Stop the background processing task."""
        if self.processing_task:
            self.processing_task.cancel()
            self.processing_task = None
            LOGGER.info("Stopped batch processing task")

    async def _process_batches(self):
        """Main batch processing loop."""
        while True:
            try:
                # Wait for at least one request
                first_request = await self.request_queue.get()

                # Collect requests for batching
                batch_requests = [first_request]

                # Try to collect more requests within timeout
                timeout_seconds = self.batch_timeout_ms / 1000.0
                deadline = asyncio.get_event_loop().time() + timeout_seconds

                while len(batch_requests) < self.max_batch_size and asyncio.get_event_loop().time() < deadline:
                    try:
                        remaining_time = deadline - asyncio.get_event_loop().time()
                        if remaining_time <= 0:
                            break

                        request = await asyncio.wait_for(self.request_queue.get(), timeout=remaining_time)
                        batch_requests.append(request)
                    except asyncio.TimeoutError:
                        break

                # Process the batch
                await self._process_batch(batch_requests)

            except asyncio.CancelledError:
                break
            except Exception as e:
                LOGGER.error(f"Error in batch processing: {str(e)}")

    async def _process_batch(self, batch_requests: list[BatchRequest]):
        """Process a batch of requests."""
        try:
            # Separate by request type
            image_requests = [r for r in batch_requests if r.request_type == "image"]
            text_requests = [r for r in batch_requests if r.request_type == "text"]

            # Process image batch
            if image_requests:
                images = [r.data for r in image_requests]
                embeddings = self._embed_images_batch(images)

                for request, embedding in zip(image_requests, embeddings):
                    await request.response_queue.put({"success": True, "embedding": embedding})

            # Process text batch
            if text_requests:
                texts = [r.data for r in text_requests]
                embeddings = self._embed_texts_batch(texts)

                for request, embedding in zip(text_requests, embeddings):
                    await request.response_queue.put({"success": True, "embedding": embedding})

        except Exception as e:
            LOGGER.error(f"Error processing batch: {str(e)}")
            # Send error to all requests in batch
            for request in batch_requests:
                await request.response_queue.put({"success": False, "error": str(e)})

    def _embed_images_batch(self, images: list[Image.Image]) -> list[list[float]]:
        """Generate embeddings for multiple images in a batch."""
        with torch.no_grad():
            inputs = self.processor(images=images, return_tensors="pt")
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            image_features = self.model.get_image_features(**inputs)
            # Normalize the features
            image_features = image_features / image_features.norm(p=2, dim=-1, keepdim=True)
            return image_features.cpu().numpy().tolist()

    def _embed_texts_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts in a batch."""
        with torch.no_grad():
            inputs = self.processor(text=texts, return_tensors="pt", padding=True, truncation=True)
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            text_features = self.model.get_text_features(**inputs)
            # Normalize the features
            text_features = text_features / text_features.norm(p=2, dim=-1, keepdim=True)
            return text_features.cpu().numpy().tolist()

    async def embed_image_async(self, image: Image.Image) -> list[float]:
        """Generate embedding for a single image (async batched)."""
        response_queue = asyncio.Queue()
        request = BatchRequest(data=image, response_queue=response_queue, request_type="image")

        await self.request_queue.put(request)
        result = await response_queue.get()

        if result["success"]:
            return result["embedding"]
        else:
            raise Exception(result["error"])

    async def embed_text_async(self, text: str) -> list[float]:
        """Generate embedding for a single text (async batched)."""
        response_queue = asyncio.Queue()
        request = BatchRequest(data=text, response_queue=response_queue, request_type="text")

        await self.request_queue.put(request)
        result = await response_queue.get()

        if result["success"]:
            return result["embedding"]
        else:
            raise Exception(result["error"])


# Global variables to hold the model and configuration
clip_server = None
server_config = {"max_batch_size": 8, "batch_timeout_ms": 2}


async def startup_event():
    """Initialize the CLIP model on server startup."""
    global clip_server, server_config

    clip_server = CLIPEmbeddingServer(
        max_batch_size=server_config["max_batch_size"], batch_timeout_ms=server_config["batch_timeout_ms"]
    )
    clip_server.start_processing()
    LOGGER.info("CLIP server initialized and batch processing started")


async def health_check(request):
    """Health check endpoint."""
    return JSONResponse({"status": "healthy", "model": clip_server.model_name if clip_server else None})


async def embed_image_endpoint(request):
    """Endpoint to embed an image."""
    try:
        data = await request.json()

        # Decode base64 image
        image_data = base64.b64decode(data["image"])
        image = Image.open(io.BytesIO(image_data))

        # Convert to RGB if necessary
        if image.mode != "RGB":
            image = image.convert("RGB")

        # Generate embedding using batched async method
        embedding = await clip_server.embed_image_async(image)

        return JSONResponse({"embedding": embedding})

    except Exception as e:
        LOGGER.error(f"Error in embed_image: {str(e)}")
        return JSONResponse({"error": str(e)}, status_code=500)


async def embed_text_endpoint(request):
    """Endpoint to embed text."""
    try:
        data = await request.json()
        text = data["text"]

        # Generate embedding using batched async method
        embedding = await clip_server.embed_text_async(text)

        return JSONResponse({"embedding": embedding})

    except Exception as e:
        LOGGER.error(f"Error in embed_text: {str(e)}")
        return JSONResponse({"error": str(e)}, status_code=500)


async def embed_texts_batch_endpoint(request):
    """Endpoint to embed multiple texts in batch."""
    try:
        data = await request.json()
        texts = data["texts"]

        # Generate embeddings using the internal batch method
        embeddings = clip_server._embed_texts_batch(texts)

        return JSONResponse({"embeddings": embeddings})

    except Exception as e:
        LOGGER.error(f"Error in embed_texts_batch: {str(e)}")
        return JSONResponse({"error": str(e)}, status_code=500)


# Create the Starlette app
app = Starlette(
    debug=False,
    routes=[
        Route("/health", health_check, methods=["GET"]),
        Route("/embed_image", embed_image_endpoint, methods=["POST"]),
        Route("/embed_text", embed_text_endpoint, methods=["POST"]),
        Route("/embed_texts_batch", embed_texts_batch_endpoint, methods=["POST"]),
    ],
    on_startup=[startup_event],
)


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="CLIP embedding server with dynamic batching")
    parser.add_argument("--max-batch-size", type=int, default=8, help="Maximum batch size for processing (default: 8)")
    parser.add_argument("--batch-timeout-ms", type=int, default=2, help="Batch timeout in milliseconds (default: 2)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to (default: 8000)")

    args = parser.parse_args()

    # Set server configuration
    server_config["max_batch_size"] = args.max_batch_size
    server_config["batch_timeout_ms"] = args.batch_timeout_ms

    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    LOGGER.info(f"Starting CLIP server with batch_size={args.max_batch_size}, timeout={args.batch_timeout_ms}ms")

    # Run the server
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
