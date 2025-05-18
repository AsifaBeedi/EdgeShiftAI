import zmq
import time
import os
from core.model import ModelInterface
import numpy as np

def run_peer(port):
    """Run a peer device instance"""
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    
    try:
        socket.bind(f"tcp://*:{port}")
        print(f"Peer running on port {port}")
        
        # Initialize model for peer
        model = ModelInterface()
        
        while True:
            message = socket.recv_json()
            if message.get('type') == 'ping':
                socket.send_json({'status': 'Active'})
            elif message.get('type') == 'task':
                # Process actual image data
                results = []
                for task in message['task']:
                    image_path = task.get('data')
                    if image_path and os.path.exists(image_path):
                        # Process the image using the model
                        input_data = model.preprocess_image(image_path)
                        model.interpreter.set_tensor(model.input_index, input_data)
                        model.interpreter.invoke()
                        output = model.interpreter.get_tensor(model.output_index)
                        
                        # Get top predictions
                        if output.ndim == 2 and output.shape[0] == 1:
                            output = output[0]
                        
                        top_k = 3
                        top_k_idx = np.argsort(output)[-top_k:][::-1]
                        
                        for idx in top_k_idx:
                            if idx < len(model.labels):
                                results.append({
                                    "class": model.labels[idx],
                                    "confidence": float(output[idx])
                                })
                
                socket.send_json({"detections": results})
    except zmq.error.ZMQError as e:
        print(f"Error starting peer on port {port}: {e}")
        print("The port may already be in use. Try a different port.")
    except KeyboardInterrupt:
        print(f"\nPeer on port {port} stopped by user.")
    except Exception as e:
        print(f"An unexpected error occurred in peer on port {port}: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print(f"Peer on port {port} shutting down ZeroMQ resources.")
        socket.close()
        context.term()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='EdgeShift Peer')
    parser.add_argument('--port', type=int, default=5556, help='Port for the peer device')
    args = parser.parse_args()
    
    run_peer(args.port) 