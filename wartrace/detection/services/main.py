import os
import json
import numpy as np
import cv2
from pathlib import Path
from typing import Dict, List, Tuple, Any, Union, Optional
import logging
import traceback
import random

from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

from ..models import Detection, ObjectDetection, ClassificationResult, SegmentationMask

logger = logging.getLogger(__name__)

# Define the paths
MODELS_ROOT = os.path.join(settings.BASE_DIR, 'detection', 'cv_models')
RESULTS_ROOT = os.path.join(settings.MEDIA_ROOT, 'detection_results')

# Ensure directories exist
os.makedirs(MODELS_ROOT, exist_ok=True)
os.makedirs(RESULTS_ROOT, exist_ok=True)

# Updated Model configuration dictionary with our specific models
MODEL_CONFIG = {
    'object_detection': {
        'yolo11m': {
            'model_path': os.path.join(MODELS_ROOT, 'yolo11m.pt'),
            'type': 'ultralytics',
            'threshold': 0.25,
            'description': 'General object recognition (people, vehicles, etc.)'
        }
    },
    'military_detection': {
        'yolo11m_military': {
            'model_path': os.path.join(MODELS_ROOT, 'yolo11m-military.pt'),
            'type': 'ultralytics',
            'threshold': 0.3,
            'description': 'Military objects detection (vehicles, weapons, soldiers, etc.)'
        }
    },
    'damage_assessment': {
        'xbd_classifier': {
            'model_path': os.path.join(MODELS_ROOT, 'xbd_damage_classifier.h5'),
            'type': 'keras',
            'labels': ['no_damage', 'minor_damage', 'major_damage', 'destroyed'],
            'description': 'Building damage assessment from satellite imagery'
        }
    },
    'emergency_recognition': {
        'emergency_net': {
            'model_path': os.path.join(MODELS_ROOT, 'emergency_net.h5'),
            'type': 'keras',
            'labels': ['normal', 'fire', 'flood', 'explosion', 'collapse', 'other_emergency'],
            'description': 'Emergency situation recognition'
        }
    }
}

# Ensure detection results directories exist
def ensure_detection_directories():
    """Make sure all required directories for detection results exist"""
    # Main results directory
    os.makedirs(RESULTS_ROOT, exist_ok=True)
    
    # Create subdirectories for each detection type
    for detector_type in MODEL_CONFIG.keys():
        detector_dir = os.path.join(RESULTS_ROOT, detector_type)
        os.makedirs(detector_dir, exist_ok=True)
    
    # Directory for classifications
    classifications_dir = os.path.join(RESULTS_ROOT, 'classifications')
    os.makedirs(classifications_dir, exist_ok=True)

# Call this function to ensure directories exist when the module is loaded
ensure_detection_directories()

# Define color palette for consistent object visualization
COLOR_PALETTE = {
    # Military objects
    'tank': (30, 30, 200),  # Red
    'military_vehicle': (30, 100, 220),  # Red-orange
    'soldier': (20, 100, 120),  # Deep blue
    'helicopter': (0, 140, 255),  # Orange
    'airplane': (0, 200, 255),  # Yellow
    'weapon': (20, 20, 180),  # Dark red
    'armored_vehicle': (50, 50, 220),  # Light red
    
    # Common objects
    'person': (0, 200, 0),  # Green
    'car': (200, 100, 0),  # Blue
    'truck': (200, 150, 0),  # Light blue
    'building': (128, 0, 128),  # Purple
    'tree': (0, 128, 0),  # Dark green
    'road': (100, 100, 100),  # Gray
    'water': (255, 0, 0),  # Blue
    'bridge': (180, 180, 0),  # Teal
    'damage': (0, 0, 200),  # Red
    
    # Default for other classes
    'default': (200, 200, 200)  # Light gray
}

class ModelService:
    """Service for handling ML model operations"""
    
    def __init__(self):
        self.loaded_models = {}
    
    def get_model(self, detector_type: str, model_name: str = None) -> Any:
        """Load and cache a model based on detector type and model name"""
        # Use first available model if model_name not specified
        if model_name is None:
            model_name = list(MODEL_CONFIG.get(detector_type, {}).keys())[0]
        
        model_key = f"{detector_type}_{model_name}"
        
        # Return cached model if already loaded
        if model_key in self.loaded_models:
            return self.loaded_models[model_key]
        
        # Get model config
        try:
            model_config = MODEL_CONFIG[detector_type][model_name]
        except KeyError:
            logger.error(f"Model not found: {detector_type}/{model_name}")
            return None
        
        # Load model based on type
        model_path = model_config['model_path']
        model_type = model_config['type']
        
        try:
            if model_type == 'ultralytics':
                try:
                    from ultralytics import YOLO
                    if os.path.exists(model_path):
                        model = YOLO(model_path)
                        logger.info(f"Loaded YOLO model from {model_path}")
                    else:
                        # If model file doesn't exist, attempt to download it
                        logger.warning(f"Model file not found at {model_path}, attempting to download")
                        model = YOLO(model_name)  # This will try to download from ultralytics
                except ImportError:
                    logger.error("Ultralytics package not installed, please install with: pip install ultralytics")
                    return None
                except Exception as e:
                    logger.error(f"Error loading YOLO model: {str(e)}")
                    logger.error(traceback.format_exc())
                    return None
            elif model_type == 'keras':
                try:
                    import tensorflow as tf
                    if os.path.exists(model_path):
                        model = tf.keras.models.load_model(model_path)
                        logger.info(f"Loaded Keras model from {model_path}")
                    else:
                        logger.error(f"Keras model file not found: {model_path}")
                        return None
                except ImportError:
                    logger.error("TensorFlow not installed, please install with: pip install tensorflow")
                    return None
                except Exception as e:
                    logger.error(f"Error loading Keras model: {str(e)}")
                    logger.error(traceback.format_exc())
                    return None
            else:
                logger.error(f"Unsupported model type: {model_type}")
                return None
                
            # Cache the loaded model
            self.loaded_models[model_key] = {
                'model': model,
                'config': model_config
            }
            
            return self.loaded_models[model_key]
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            logger.error(traceback.format_exc())
            return None
    
    def process_image(self, file_path: str, detector_types: List[str]) -> Dict[str, Any]:
        """
        Process an image with multiple detector types
        
        Args:
            file_path: Path to the image file
            detector_types: List of detector types to use
            
        Returns:
            Dictionary of results per detector type
        """
        logger.info(f"Processing image {file_path} with detector types: {detector_types}")
        results = {}
        
        # Process each detector type
        for detector_type in detector_types:
            if detector_type not in MODEL_CONFIG:
                logger.warning(f"Unknown detector type: {detector_type}")
                continue
                
            # Get the first model for this detector type
            model_name = list(MODEL_CONFIG[detector_type].keys())[0]
            model_data = self.get_model(detector_type, model_name)
            
            if not model_data:
                logger.warning(f"No model loaded for {detector_type}, skipping")
                continue
                
            model = model_data['model']
            config = model_data['config']
            
            # Process with the appropriate method based on detector type
            try:
                if detector_type in ['object_detection', 'military_detection']:
                    if config['type'] == 'ultralytics':
                        # Process with YOLO model
                        result = self._process_with_yolo(file_path, detector_type, model, config)
                    else:
                        logger.warning(f"Unsupported model type for {detector_type}: {config['type']}")
                        continue
                elif detector_type in ['damage_assessment', 'emergency_recognition']:
                    if config['type'] == 'keras':
                        # Process with Keras model
                        result = self._process_with_keras(file_path, detector_type, model, config)
                    else:
                        logger.warning(f"Unsupported model type for {detector_type}: {config['type']}")
                        continue
                
                results[detector_type] = {
                    'model_name': model_name,
                    'result': result
                }
                
            except Exception as e:
                logger.error(f"Error processing {detector_type} for {file_path}: {str(e)}")
                logger.error(traceback.format_exc())
        
        return results
    
    def _process_with_yolo(self, file_path: str, detector_type: str, model, config: Dict) -> Dict:
        """Process an image with a YOLO model"""
        # Generate output filename and path
        file_stem = Path(file_path).stem
        output_filename = f"{file_stem}_{detector_type}.jpg"
        
        # Store in detector-specific subfolder
        output_dir = os.path.join(RESULTS_ROOT, detector_type)
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, output_filename)
        
        try:
            # Run inference with the model
            threshold = config.get('threshold', 0.25)
            results = model(file_path, conf=threshold)
            
            # Read original image for annotation
            original_img = cv2.imread(file_path)
            if original_img is None:
                logger.error(f"Failed to read image: {file_path}")
                raise ValueError(f"Could not read image file: {file_path}")
            
            # Extract detection results
            detections = []
            result = results[0]  # First image result
            
            # Convert YOLO results to our format
            for box in result.boxes:
                label_idx = int(box.cls)
                label = result.names[label_idx]
                conf = float(box.conf)
                
                # Get coordinates (convert to pixels)
                x1, y1, x2, y2 = box.xyxy[0].tolist()  # xyxy format (top-left, bottom-right)
                
                detections.append({
                    'label': label,
                    'confidence': conf,
                    'bbox': [x1, y1, x2, y2]
                })
            
            # Draw annotations on the image
            annotated_img = self._draw_beautiful_annotations(original_img.copy(), detections, detector_type)
            
            # Save the annotated image
            cv2.imwrite(output_path, annotated_img)
            
            # Define the URL path for accessing the result
            relative_path = f"detection_results/{detector_type}/{output_filename}"
            
            # Create summary text
            label_counts = {}
            for det in detections:
                label = det['label']
                label_counts[label] = label_counts.get(label, 0) + 1
            
            summary_parts = []
            for label, count in label_counts.items():
                summary_parts.append(f"{count} {label}{'s' if count > 1 else ''}")
            
            summary = f"Found {len(detections)} objects: " + ", ".join(summary_parts) if detections else "No objects detected"
            
            return {
                'detections': detections,
                'output_path': output_path,
                'relative_path': relative_path,
                'summary': summary
            }
            
        except Exception as e:
            logger.error(f"Error in YOLO processing: {str(e)}")
            logger.error(traceback.format_exc())
            
            # Create error image
            error_img = np.zeros((400, 600, 3), dtype=np.uint8)
            cv2.putText(
                error_img, 
                f"Error processing image with {detector_type}", 
                (20, 150), 
                cv2.FONT_HERSHEY_SIMPLEX, 
                0.7, 
                (255, 255, 255), 
                1
            )
            cv2.putText(
                error_img, 
                str(e), 
                (20, 200), 
                cv2.FONT_HERSHEY_SIMPLEX, 
                0.5, 
                (200, 100, 100), 
                1
            )
            
            # Save error image
            cv2.imwrite(output_path, error_img)
            
            relative_path = f"detection_results/{detector_type}/{output_filename}"
            
            return {
                'detections': [],
                'output_path': output_path,
                'relative_path': relative_path,
                'summary': f"Error processing image: {str(e)}"
            }
    
    def _process_with_keras(self, file_path: str, detector_type: str, model, config: Dict) -> Dict:
        """Process an image with a Keras classification model"""
        # Store result in detector-specific subfolder
        file_stem = Path(file_path).stem
        output_filename = f"{file_stem}_{detector_type}.jpg"
        output_dir = os.path.join(RESULTS_ROOT, detector_type)
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, output_filename)
        
        try:
            # Get labels from config
            labels = config.get('labels', [])
            if not labels:
                raise ValueError("No class labels defined for the model")
            
            # Preprocess image for the model
            import tensorflow as tf
            img = tf.keras.preprocessing.image.load_img(file_path, target_size=(224, 224))
            img_array = tf.keras.preprocessing.image.img_to_array(img)
            img_array = np.expand_dims(img_array, 0)  # Create batch dimension
            img_array = img_array / 255.0  # Normalize
            
            # Run prediction
            predictions = model.predict(img_array)
            
            # Get prediction results
            if predictions.shape[1] != len(labels):
                logger.warning(f"Model output shape {predictions.shape[1]} doesn't match number of labels {len(labels)}")
                
            # For multi-class, use argmax to get the most likely class
            if len(predictions.shape) == 2:
                main_idx = np.argmax(predictions[0])
                main_class = labels[main_idx] if main_idx < len(labels) else f"class_{main_idx}"
                main_confidence = float(predictions[0][main_idx])
                
                # Create all predictions dictionary
                all_predictions = {}
                for i, conf in enumerate(predictions[0]):
                    if i < len(labels):
                        all_predictions[labels[i]] = float(conf)
                    else:
                        all_predictions[f"class_{i}"] = float(conf)
                
            # Create a visualization of the classification result
            self._create_classification_visualization(
                file_path, 
                output_path, 
                detector_type, 
                main_class, 
                all_predictions
            )
            
            # Define the URL path for accessing the result
            relative_path = f"detection_results/{detector_type}/{output_filename}"
            
            return {
                'class': main_class,
                'confidence': main_confidence,
                'all_predictions': all_predictions,
                'relative_path': relative_path
            }
            
        except Exception as e:
            logger.error(f"Error in Keras processing: {str(e)}")
            logger.error(traceback.format_exc())
            
            # Create error image
            error_img = np.zeros((400, 600, 3), dtype=np.uint8)
            cv2.putText(
                error_img, 
                f"Error in {detector_type} classification", 
                (20, 150), 
                cv2.FONT_HERSHEY_SIMPLEX, 
                0.7, 
                (255, 255, 255), 
                1
            )
            cv2.putText(
                error_img, 
                str(e), 
                (20, 200), 
                cv2.FONT_HERSHEY_SIMPLEX, 
                0.5, 
                (200, 100, 100), 
                1
            )
            
            # Save error image
            cv2.imwrite(output_path, error_img)
            
            relative_path = f"detection_results/{detector_type}/{output_filename}"
            
            return {
                'class': 'error',
                'confidence': 0.0,
                'all_predictions': {'error': 1.0},
                'relative_path': relative_path
            }
    
    def _draw_beautiful_annotations(self, img, detections, detector_type):
        """Draw beautiful annotations on the image"""
        # Create a slightly darker copy for better contrast of the annotations
        overlay = img.copy()
        h, w = img.shape[:2]
        
        # Add a title/header based on detector type
        header_bg_color = (50, 50, 50) if detector_type == 'object_detection' else (40, 20, 60)
        header_text_color = (255, 255, 255)
        
        header_text = "General Object Detection" if detector_type == 'object_detection' else "Military Object Detection"
        
        # Add a header/title bar
        cv2.rectangle(img, (0, 0), (w, 40), header_bg_color, -1)
        cv2.putText(img, header_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, header_text_color, 2)
        
        # Add objects detected
        for i, det in enumerate(detections):
            x_min, y_min, x_max, y_max = map(int, det['bbox'])
            label = det['label']
            confidence = det['confidence']
            
            # Get color for this class
            color = COLOR_PALETTE.get(label.lower(), COLOR_PALETTE['default'])
            
            # Draw slightly transparent polygon for each object
            pts = np.array([[x_min, y_min], [x_max, y_min], [x_max, y_max], [x_min, y_max]], np.int32)
            cv2.fillPoly(overlay, [pts], color)
            
            # Draw bounding box
            box_thickness = 2
            cv2.rectangle(img, (x_min, y_min), (x_max, y_max), color, box_thickness)
            
            # Prepare label text
            label_text = f"{label} {confidence:.2f}"
            
            # Draw filled rectangle for the label
            label_size, _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(
                img,
                (x_min, y_min - label_size[1] - 5),
                (x_min + label_size[0] + 5, y_min),
                color,
                -1
            )
            
            # Draw the label text in white
            cv2.putText(
                img,
                label_text,
                (x_min + 3, y_min - 4),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 255),
                1
            )
        
        # Blend overlay with the original image for a semi-transparent effect
        alpha = 0.3  # Transparency level
        cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0, img)
        
        # Add footer with model info
        model_info = f"Model: {MODEL_CONFIG[detector_type][list(MODEL_CONFIG[detector_type].keys())[0]]['description']}"
        footer_y = h - 20
        
        # Add a footer bar
        cv2.rectangle(img, (0, h-40), (w, h), header_bg_color, -1)
        cv2.putText(img, model_info, (10, footer_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, header_text_color, 1)
        cv2.putText(img, f"Objects: {len(detections)}", (w-150, footer_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, header_text_color, 1)
        
        return img
    
    def _create_classification_visualization(self, input_path, output_path, detector_type, main_class, predictions):
        """Create a visualization for classification results"""
        try:
            # Read input image
            img = cv2.imread(input_path)
            if img is None:
                img = np.zeros((400, 600, 3), dtype=np.uint8)
            
            h, w = img.shape[:2]
            
            # Make a clean copy
            result_img = img.copy()
            
            # Add header with classification type
            header_text = "Damage Assessment" if detector_type == "damage_assessment" else "Emergency Recognition"
            cv2.rectangle(result_img, (0, 0), (w, 40), (40, 40, 40), -1)
            cv2.putText(result_img, header_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
            
            # Add a semi-transparent overlay with the classification result
            overlay = img.copy()
            
            # Determine color based on class
            if detector_type == "damage_assessment":
                if main_class == "no_damage":
                    color = (0, 255, 0)  # Green
                elif main_class == "minor_damage":
                    color = (0, 255, 255)  # Yellow
                elif main_class == "major_damage":
                    color = (0, 128, 255)  # Orange
                else:  # destroyed
                    color = (0, 0, 255)  # Red
            else:  # emergency recognition
                if main_class == "normal":
                    color = (0, 255, 0)  # Green
                elif main_class == "fire":
                    color = (0, 0, 255)  # Red
                elif main_class == "flood":
                    color = (255, 0, 0)  # Blue
                elif main_class == "explosion":
                    color = (0, 0, 180)  # Dark red
                else:
                    color = (128, 0, 128)  # Purple
            
            # Create a colored border
            border_size = 20
            cv2.rectangle(result_img, (0, 0), (w, h), color, border_size)
            
            # Add classification label
            formatted_class = main_class.replace('_', ' ').title()
            conf = predictions[main_class]
            label_text = f"{formatted_class} ({conf:.1%})"
            
            # Add a bottom info panel with classification results
            cv2.rectangle(result_img, (0, h-100), (w, h), (40, 40, 40), -1)
            cv2.putText(result_img, "Classification:", (20, h-70), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            cv2.putText(result_img, label_text, (20, h-30), cv2.FONT_HERSHEY_SIMPLEX, 1.2, color, 2)
            
            # Add confidence bar
            bar_length = int(w - 40)
            bar_height = 20
            bar_x = 20
            bar_y = h - 130
            
            # Draw background
            cv2.rectangle(result_img, (bar_x, bar_y), (bar_x + bar_length, bar_y + bar_height), (100, 100, 100), -1)
            
            # Draw filled portion
            filled_length = int(bar_length * conf)
            cv2.rectangle(result_img, (bar_x, bar_y), (bar_x + filled_length, bar_y + bar_height), color, -1)
            
            cv2.imwrite(output_path, result_img)
            
        except Exception as e:
            logger.error(f"Error creating classification visualization: {str(e)}")
            logger.error(traceback.format_exc())

# Singleton instance
model_service = ModelService()


def process_marker_file(marker_file, detector_types: List[str]) -> List[Detection]:
    """
    Process a marker file with the requested detector types
    
    Args:
        marker_file: MarkerFile instance
        detector_types: List of detector types to use
        
    Returns:
        List of created Detection objects
    """
    logger.info(f"Processing file ID {marker_file.id} with detector types: {detector_types}")
    
    # Check if file exists
    if not marker_file.file:
        logger.warning(f"File not found: {marker_file.id}")
        return []
    
    try:
        file_path = marker_file.file.path
        if not os.path.exists(file_path):
            logger.warning(f"File does not exist on disk: {file_path}")
            return []
            
        file_ext = os.path.splitext(file_path)[1].lower()
        
        # Check if it's a processable image
        processable_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff', '.webp']
        if file_ext not in processable_extensions:
            logger.warning(f"Skipping non-processable file: {file_path} (format: {file_ext})")
            return []
        
        # Process with model service
        try:
            logger.info(f"Calling model service for file {marker_file.id}")
            results = model_service.process_image(file_path, detector_types)
            logger.info(f"Got results for detector types: {list(results.keys())}")
        except Exception as e:
            logger.error(f"Error in model processing: {str(e)}")
            logger.error(traceback.format_exc())
            return []
        
        # Create detection records
        detection_objects = []
        
        for detector_type, result_data in results.items():
            try:
                logger.info(f"Creating detection record for {detector_type}")
                
                # Create base detection record
                detection = Detection(
                    marker_file=marker_file,
                    detector_type=detector_type,
                    model_name=result_data['model_name']
                )
                
                result = result_data['result']
                
                # Handle different detector types
                if detector_type in ['object_detection', 'military_detection']:
                    # Store overall summary
                    detection.summary = result.get('summary', '')
                    
                    # Store the relative path for serving via URL
                    if 'relative_path' in result:
                        detection.image_path = result['relative_path']
                        
                    detection.save()
                    logger.info(f"Saved detection ID {detection.id}")
                    
                    # Store individual detections
                    for det in result.get('detections', []):
                        object_detection = ObjectDetection.objects.create(
                            detection=detection,
                            label=det['label'],
                            confidence=det['confidence'],
                            x_min=det['bbox'][0],
                            y_min=det['bbox'][1],
                            x_max=det['bbox'][2],
                            y_max=det['bbox'][3]
                        )
                        logger.info(f"Created object detection {object_detection.id}: {det['label']}")
                    
                elif detector_type in ['damage_assessment', 'emergency_recognition']:
                    # Store classification result
                    detection.summary = f"Classified as {result['class']} with {result['confidence']:.2f} confidence"
                    
                    # Store the relative path for serving via URL
                    if 'relative_path' in result:
                        detection.image_path = result['relative_path']
                        
                    detection.save()
                    logger.info(f"Saved detection ID {detection.id}")
                    
                    classification = ClassificationResult.objects.create(
                        detection=detection,
                        label=result['class'],
                        confidence=result['confidence']
                    )
                    logger.info(f"Created classification {classification.id}: {result['class']}")
                    
                    # Store all prediction confidences if available
                    if 'all_predictions' in result:
                        for label, conf in result['all_predictions'].items():
                            if label != result['class']:  # Main prediction already stored
                                ClassificationResult.objects.create(
                                    detection=detection,
                                    label=label,
                                    confidence=conf
                                )
                
                detection_objects.append(detection)
                
            except Exception as e:
                logger.error(f"Error creating detection record: {str(e)}")
                logger.error(traceback.format_exc())
        
        return detection_objects
        
    except Exception as e:
        logger.error(f"Error in process_marker_file: {str(e)}")
        logger.error(traceback.format_exc())
        return []


def process_marker(marker) -> Dict[str, int]:
    """
    Process all files for a marker based on its detection settings
    
    Args:
        marker: Marker instance
        
    Returns:
        Summary of processed files and detections
    """
    logger.info(f"Starting process_marker for marker ID {marker.id}")
    
    detector_types = []
    
    # Check which detector types are enabled - use the correct field names
    if marker.object_detection:
        detector_types.append('object_detection')
    if marker.camouflage_detection:  # Model field name
        detector_types.append('military_detection')  # Detector type name
    if marker.damage_assessment:
        detector_types.append('damage_assessment')
    if marker.thermal_analysis:  # Model field name
        detector_types.append('emergency_recognition')  # Detector type name
    
    logger.info(f"Enabled detector types: {detector_types}")
    
    if not detector_types:
        logger.info(f"No AI detection options enabled for marker {marker.id}")
        return {'processed': 0, 'detections': 0, 'already_processed': 0}
    
    # Process all files
    processed_count = 0
    detection_count = 0
    error_count = 0
    
    # Simplified approach: process all files without checking for existing detections
    for marker_file in marker.files.all():
        try:
            file_path = marker_file.file.path
            # Check if the file exists
            if not os.path.exists(file_path):
                logger.warning(f"File not found on disk: {file_path}")
                error_count += 1
                continue
                
            logger.info(f"Processing file {marker_file.id} with detector types {detector_types}")
            detections = process_marker_file(marker_file, detector_types)
            
            if detections:
                processed_count += 1
                detection_count += len(detections)
                logger.info(f"Created {len(detections)} detections for file {marker_file.id}")
            else:
                logger.info(f"No detections created for file {marker_file.id}")
                
        except Exception as e:
            logger.error(f"Error processing file {marker_file.id}: {str(e)}")
            logger.error(traceback.format_exc())
            error_count += 1
    
    result = {
        'processed': processed_count,
        'detections': detection_count,
        'errors': error_count
    }
    
    logger.info(f"Finished processing marker {marker.id}: {result}")
    return result
