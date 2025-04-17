import json
import os
import traceback
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.db import models
from django.conf import settings

from content.models import Marker, MarkerFile
from .models import Detection, ObjectDetection, ClassificationResult
from .services.main import process_marker, process_marker_file, model_service, MODEL_CONFIG, ensure_detection_directories

# Set up logging
logger = logging.getLogger(__name__)

@login_required
@require_http_methods(["POST"])
def process_marker_api(request, marker_id):
    """API endpoint to process a marker's files with AI"""
    marker = get_object_or_404(Marker, id=marker_id)
    
    # Ensure detection directories exist
    ensure_detection_directories()
    
    # Debug message
    logger.info(f"Processing marker ID: {marker_id}")
    
    # Security check - only owner or staff can process
    if marker.user != request.user and not request.user.is_staff:
        logger.warning(f"Permission denied for user {request.user.username} on marker {marker_id}")
        return JsonResponse({'success': False, 'message': 'Permission denied'}, status=403)
    
    try:
        # Check which detector types are enabled in the marker
        detector_types = []
        if marker.object_detection:
            detector_types.append('object_detection')
        if marker.camouflage_detection:
            detector_types.append('military_detection')
        if marker.damage_assessment:
            detector_types.append('damage_assessment')
        if marker.thermal_analysis:
            detector_types.append('emergency_recognition')
        
        logger.info(f"Enabled detector types: {detector_types}")
        
        if not detector_types:
            logger.warning(f"No AI detection options enabled for marker {marker_id}")
            return JsonResponse({
                'success': False,
                'message': 'No AI detection options enabled for this marker'
            }, status=400)
        
        # Process the marker
        logger.info(f"Starting processing for marker {marker_id}")
        try:
            results = process_marker(marker)
            logger.info(f"Processing results: {results}")
        except Exception as e:
            logger.error(f"Error in process_marker: {str(e)}")
            logger.error(traceback.format_exc())
            return JsonResponse({
                'success': False,
                'message': f"Error in processing: {str(e)}"
            }, status=500)
        
        # For object detection results, add the annotated images to the marker's media
        processed_files = 0
        
        try:
            # Get all the newly created detections for this marker using the proper join
            marker_files = MarkerFile.objects.filter(marker=marker)
            detections = Detection.objects.filter(marker_file__in=marker_files)
            
            # Filter for appropriate types of detections
            detections = detections.filter(
                detector_type__in=['object_detection', 'military_detection', 'damage_assessment', 'emergency_recognition']
            )
            logger.info(f"Found {len(detections)} detections for processing")
            
            # Process each detection
            for detection in detections:
                try:
                    if detection.image_path and detection.image_path.strip():
                        # Use the correct path to access the file - handle both absolute and relative paths
                        image_path = detection.image_path
                        if image_path.startswith('/'):
                            image_path = image_path[1:]  # Remove leading slash
                        
                        # Form the full path to the result image
                        full_path = os.path.join(settings.MEDIA_ROOT, image_path)
                        logger.info(f"Checking file path: {full_path}")
                        
                        if os.path.exists(full_path):
                            try:
                                # Create unique filename with detector type
                                detector_name = detection.detector_type.replace('_', '-')
                                file_name = f"ai_{detector_name}_{detection.id}.jpg"
                                
                                # Check if we already have this processed image
                                existing = MarkerFile.objects.filter(
                                    marker=marker, 
                                    file__contains=f"ai_{detector_name}_{detection.id}"
                                ).exists()
                                
                                if not existing:
                                    logger.info(f"Creating new marker file: {file_name}")
                                    # Open the file and create a new MarkerFile
                                    with open(full_path, 'rb') as f:
                                        file_content = f.read()
                                        new_file = MarkerFile.objects.create(
                                            marker=marker,
                                            file=ContentFile(file_content, name=file_name)
                                        )
                                        logger.info(f"Created marker file {new_file.id}")
                                        processed_files += 1
                                else:
                                    logger.info(f"File already exists: {file_name}")
                            except Exception as e:
                                logger.error(f"Error saving processed file: {str(e)}")
                                logger.error(traceback.format_exc())
                        else:
                            logger.warning(f"File does not exist: {full_path}")
                            # Try alternate path construction if the file wasn't found
                            alt_path = os.path.join(settings.BASE_DIR, 'media', image_path)
                            if os.path.exists(alt_path):
                                logger.info(f"Found file at alternate path: {alt_path}")
                                try:
                                    file_name = f"ai_{detection.detector_type}_{detection.id}.jpg"
                                    
                                    # Check if we already have this processed image
                                    existing = MarkerFile.objects.filter(
                                        marker=marker, 
                                        file__contains=file_name
                                    ).exists()
                                    
                                    if not existing:
                                        with open(alt_path, 'rb') as f:
                                            file_content = f.read()
                                            new_file = MarkerFile.objects.create(
                                                marker=marker,
                                                file=ContentFile(file_content, name=file_name)
                                            )
                                            logger.info(f"Created marker file {new_file.id} from alternate path")
                                            processed_files += 1
                                except Exception as e:
                                    logger.error(f"Error saving processed file from alternate path: {str(e)}")
                except Exception as det_e:
                    logger.error(f"Error processing detection {detection.id}: {str(det_e)}")
                    logger.error(traceback.format_exc())
        except Exception as e:
            logger.error(f"Error in file processing: {str(e)}")
            logger.error(traceback.format_exc())
        
        logger.info(f"Added {processed_files} result images")
        
        return JsonResponse({
            'success': True,
            'message': f"Processed {results['processed']} files with {results['detections']} detections. Added {processed_files} result images.",
            'results': results
        })
        
    except Exception as e:
        logger.error(f"Error processing marker {marker_id}: {str(e)}")
        logger.error(traceback.format_exc())
        return JsonResponse({
            'success': False,
            'message': f"Error processing marker: {str(e)}"
        }, status=500)


@login_required
@require_http_methods(["GET"])
def marker_detection_results(request, marker_id):
    """View detection results for a specific marker"""
    marker = get_object_or_404(Marker, id=marker_id)
    logger.info(f"Viewing detection results for marker {marker_id}")
    
    # Security check - only owner or staff can view
    if marker.user != request.user and not request.user.is_staff:
        return JsonResponse({'success': False, 'message': 'Permission denied'}, status=403)
    
    # Get all detections for this marker's files
    files_with_detections = []
    
    for marker_file in marker.files.all():
        # Direct query to avoid related_name issues
        detections = Detection.objects.filter(marker_file_id=marker_file.id)
        if detections:
            detection_data = []
            
            for detection in detections:
                # Get objects for this detection
                objects = list(ObjectDetection.objects.filter(detection=detection).values(
                    'label', 'confidence', 'x_min', 'y_min', 'x_max', 'y_max'
                ))
                
                # Get classifications for this detection
                classifications = list(ClassificationResult.objects.filter(detection=detection).values(
                    'label', 'confidence'
                ))
                
                # Get model description
                model_description = ""
                if detection.detector_type in MODEL_CONFIG:
                    if detection.model_name in MODEL_CONFIG[detection.detector_type]:
                        model_description = MODEL_CONFIG[detection.detector_type][detection.model_name].get('description', '')
                
                # Create full URL path for the image
                image_url = None
                if detection.image_path:
                    # Handle relative paths
                    image_path = detection.image_path
                    if image_path.startswith('/'):
                        image_path = image_path[1:]
                    image_url = f"{settings.MEDIA_URL}{image_path}"
                
                # Get the display name for the detector type
                detector_display_name = detection.detector_type.replace('_', ' ').title()
                
                detection_data.append({
                    'id': detection.id,
                    'detector_type': detection.detector_type,
                    'detector_display_name': detector_display_name,
                    'model_name': detection.model_name,
                    'model_description': model_description,
                    'summary': detection.summary,
                    'image_path': detection.image_path,
                    'image_url': image_url,
                    'objects': objects,
                    'classifications': classifications,
                    'is_object_detection': detection.detector_type in ['object_detection', 'military_detection'],
                    'is_classification': detection.detector_type in ['damage_assessment', 'emergency_recognition']
                })
            
            files_with_detections.append({
                'file': marker_file,
                'detections': detection_data
            })
    
    # Get all detector types
    detector_types = {
        detector_type: {
            'name': detector_type.replace('_', ' ').title(),
            'description': next(iter(models.values())).get('description', '')
        }
        for detector_type, models in MODEL_CONFIG.items()
    }
    
    return render(request, 'detection/marker_results.html', {
        'marker': marker,
        'files_with_detections': files_with_detections,
        'detector_types': detector_types
    })


@login_required
@require_http_methods(["GET"])
def available_models(request):
    """API endpoint to get available models information"""
    models_info = {}
    
    for detector_type, models in MODEL_CONFIG.items():
        models_info[detector_type] = {
            'name': detector_type.replace('_', ' ').title(),
            'description': next(iter(models.values())).get('description', ''),
            'models': [
                {
                    'name': model_name,
                    'description': model_config.get('description', '')
                }
                for model_name, model_config in models.items()
            ]
        }
    
    return JsonResponse({'models': models_info})


@login_required
@require_http_methods(["POST"])
def process_single_file(request, file_id):
    """Process a single file with AI detection"""
    marker_file = get_object_or_404(MarkerFile, id=file_id)
    marker = marker_file.marker
    
    # Ensure detection directories exist
    ensure_detection_directories()
    
    logger.info(f"Processing single file ID: {file_id} for marker {marker.id}")
    
    # Security check - only owner or staff can process
    if marker.user != request.user and not request.user.is_staff:
        return JsonResponse({'success': False, 'message': 'Permission denied'}, status=403)
    
    # Determine which detector types to use based on marker settings
    detector_types = []
    if marker.object_detection:
        detector_types.append('object_detection')
    if marker.camouflage_detection:
        detector_types.append('military_detection')
    if marker.damage_assessment:
        detector_types.append('damage_assessment')
    if marker.thermal_analysis:
        detector_types.append('emergency_recognition')
    
    logger.info(f"Detector types: {detector_types}")
    
    if not detector_types:
        return JsonResponse({
            'success': False,
            'message': 'No AI detection options enabled for this marker'
        }, status=400)
    
    try:
        # Process the file with all detector types
        logger.info(f"Processing file with detector types: {detector_types}")
        detections = process_marker_file(marker_file, detector_types)
        logger.info(f"Created {len(detections)} detections")
        
        # Add processed images as new marker files
        processed_files = 0
        for detection in detections:
            if detection.image_path:
                # Use the correct path to access the file
                image_path = detection.image_path
                if image_path.startswith('/'):
                    image_path = image_path[1:]  # Remove leading slash
                
                # Try multiple possible path constructions to find the file
                possible_paths = [
                    os.path.join(settings.MEDIA_ROOT, image_path),
                    os.path.join(settings.BASE_DIR, 'media', image_path),
                ]
                
                file_found = False
                for full_path in possible_paths:
                    if os.path.exists(full_path):
                        try:
                            # Create unique filename with timestamp to avoid conflicts
                            import time
                            timestamp = int(time.time())
                            file_name = f"{detection.detector_type}_{detection.id}_{timestamp}.jpg"
                            
                            # Add the file to the marker
                            with open(full_path, 'rb') as f:
                                MarkerFile.objects.create(
                                    marker=marker,
                                    file=ContentFile(f.read(), name=file_name)
                                )
                                processed_files += 1
                                logger.info(f"Created file: {file_name}")
                            
                            file_found = True
                            break  # Found and processed the file, no need to try other paths
                        except Exception as e:
                            logger.error(f"Error creating file from {full_path}: {str(e)}")
                
                if not file_found:
                    logger.warning(f"Could not find result image at any expected location for detection {detection.id}")
        
        return JsonResponse({
            'success': True,
            'message': f"Processed file with {len(detections)} detection results. Added {processed_files} images.",
            'detection_count': len(detections)
        })
    except Exception as e:
        logger.error(f"Error in process_single_file: {str(e)}")
        logger.error(traceback.format_exc())
        return JsonResponse({
            'success': False,
            'message': f"Error processing file: {str(e)}"
        }, status=500)
