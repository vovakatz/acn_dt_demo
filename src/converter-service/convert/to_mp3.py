import pika, json, tempfile, os
from bson.objectid import ObjectId
import moviepy.editor

def start(message, fs_videos, fs_mp3s, channel, logger):
    try:
        message_data = json.loads(message)
        video_id = message_data.get("video_fid")
        
        logger.info("Starting conversion process", extra={
            'video_id': video_id
        })
        
        # Get the video from GridFS
        logger.debug(f"Retrieving video from GridFS", extra={'video_id': video_id})
        try:
            out = fs_videos.get(ObjectId(video_id))
        except Exception as e:
            logger.error(f"Failed to retrieve video from GridFS: {str(e)}", extra={'video_id': video_id})
            return f"Failed to retrieve video: {str(e)}"
        
        # Create temporary file for video processing
        logger.debug("Creating temporary file")
        tf = tempfile.NamedTemporaryFile()
        
        # Write video content to temporary file
        tf.write(out.read())
        
        # Extract audio from video
        logger.info("Extracting audio from video", extra={'video_id': video_id})
        try:
            audio = moviepy.editor.VideoFileClip(tf.name).audio
            tf.close()
        except Exception as e:
            logger.error(f"Failed to extract audio: {str(e)}", extra={'video_id': video_id})
            return f"Failed to extract audio: {str(e)}"
        
        # Create MP3 file
        tf_path = tempfile.gettempdir() + f"/{video_id}.mp3"
        logger.info("Writing audio to MP3 file", extra={
            'video_id': video_id, 
            'mp3_path': tf_path
        })
        
        try:
            audio.write_audiofile(tf_path)
        except Exception as e:
            logger.error(f"Failed to write audio file: {str(e)}", extra={'video_id': video_id})
            return f"Failed to write audio file: {str(e)}"
        
        # Save MP3 to MongoDB
        logger.info("Saving MP3 to GridFS", extra={'video_id': video_id})
        try:
            f = open(tf_path, "rb")
            data = f.read()
            mp3_id = fs_mp3s.put(data)
            f.close()
            
            # Remove temporary MP3 file
            os.remove(tf_path)
            
            logger.debug("MP3 saved successfully", extra={
                'video_id': video_id,
                'mp3_id': str(mp3_id)
            })
            
            # Update message with MP3 ID
            message_data["mp3_fid"] = str(mp3_id)
            
        except Exception as e:
            logger.error(f"Failed to save MP3 to GridFS: {str(e)}", extra={'video_id': video_id})
            return f"Failed to save MP3: {str(e)}"
        
        # Publish message to MP3 queue
        mp3_queue = os.environ.get("MP3_QUEUE")
        logger.info("Publishing message to MP3 queue", extra={
            'video_id': video_id,
            'mp3_id': str(mp3_id),
            'queue': mp3_queue
        })
        
        try:
            channel.basic_publish(
                exchange="",
                routing_key=mp3_queue,
                body=json.dumps(message_data),
                properties=pika.BasicProperties(
                    delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE
                ),
            )
            
            logger.info("Conversion completed successfully", extra={
                'video_id': video_id,
                'mp3_id': str(mp3_id)
            })
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to publish message: {str(e)}", extra={
                'video_id': video_id,
                'mp3_id': str(mp3_id)
            })
            
            # Cleanup: delete MP3 file from GridFS if message publishing fails
            logger.debug("Cleaning up MP3 from GridFS after publish failure", extra={'mp3_id': str(mp3_id)})
            fs_mp3s.delete(mp3_id)
            
            return f"Failed to publish message: {str(e)}"
            
    except json.JSONDecodeError as e:
        logger.error(f"Invalid message format: {str(e)}")
        return f"Invalid message format: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error in conversion process: {str(e)}")
        return f"Unexpected error: {str(e)}"
