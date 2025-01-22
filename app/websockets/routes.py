from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.websockets.connection_manager import manager
from app.image_processing.product_image_generator import generate_ad_photo, add_source_photo
import logging
import base64
router = APIRouter()
logger = logging.getLogger(__name__)

@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    try:
        await websocket.accept()  # Accept the connection first
        await manager.connect(websocket, client_id)
        logger.info(f"Client {client_id} connected")
        
        while True:
            try:
                if websocket.client_state.value == 3:  # Check if disconnected before receiving
                    logger.info(f"Client {client_id} disconnected, breaking receive loop")
                    break
                    
                data = await websocket.receive_json()
                # Handle different types of messages
                if data.get("type") == "broadcast":
                    await manager.broadcast(data)
                elif data.get("type") == "generate_ad_photos":
                    # Extract image and background description from the data
                    image = data.get("image")
                    product_id = data.get("product_id")
                    background_description = data.get("background_description")
                    auth = data.get("auth")
                    
                    if not all([image, product_id, auth]) or not all([auth.get("access_token"), auth.get("refresh_token")]):
                        raise ValueError("Image, product ID, and auth tokens are required")
                    
                    # Process the image with the background description
                    result = await generate_ad_photo(
                        image=image, 
                        background_description=background_description, 
                        product_id=product_id,
                        access_token=auth["access_token"],
                        refresh_token=auth["refresh_token"]
                    )
                    if websocket.client_state.value != 3:  # Check if still connected before sending
                        await manager.send_personal_message({
                            "type": "process_complete",
                            "data": result
                        }, websocket)
                elif data.get("type") == "add_source_photo":
                    image = data.get("image")
                    product_id = data.get("product_id")
                    auth = data.get("auth")
                    
                    if not all([image, product_id, auth]) or not all([auth.get("access_token"), auth.get("refresh_token")]):
                        raise ValueError("Image, product ID, and auth tokens are required")
                        
                    result = await add_source_photo(
                        image=image,
                        access_token=auth["access_token"],
                        refresh_token=auth["refresh_token"],
                        product_id=product_id
                    )
                    if websocket.client_state.value != 3:  # Check if still connected before sending
                        await manager.send_personal_message({
                            "type": "process_complete",
                            "data": result
                        }, websocket)
                else:
                    if websocket.client_state.value != 3:  # Check if still connected before sending
                        await manager.send_personal_message(data, websocket)
            except WebSocketDisconnect:
                logger.info(f"Client {client_id} disconnected during message processing")
                break  # Break the receive loop on disconnect
            except Exception as e:
                logger.error(f"Error processing message from client {client_id}: {str(e)}")
                if websocket.client_state.value != 3:  # Check if still connected before sending error
                    try:
                        await manager.send_personal_message({
                            "type": "error",
                            "data": {"message": str(e)}
                        }, websocket)
                    except Exception as send_error:
                        logger.error(f"Failed to send error message: {str(send_error)}")
                        break  # Break the loop if we can't send messages
    except WebSocketDisconnect:
        logger.info(f"Client {client_id} disconnected")
    except Exception as e:
        logger.error(f"Unexpected error with client {client_id}: {str(e)}")
    finally:
        # Clean up in all cases
        await manager.disconnect(websocket, client_id)
        try:
            if websocket.client_state.value != 3:
                await websocket.close()
        except:
            pass 