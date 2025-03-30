import React, { useState } from 'react';
import { uploadService } from '../services/api';

const VideoUpload: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState<boolean>(false);
  const [uploadStatus, setUploadStatus] = useState<{
    success: boolean;
    message: string;
  } | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0]);
      setUploadStatus(null);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!file) {
      setUploadStatus({
        success: false,
        message: 'Please select a file to upload',
      });
      return;
    }

    setUploading(true);
    setUploadStatus(null);
    
    try {
      const response = await uploadService.uploadVideo(file);
      setUploadStatus({
        success: true,
        message: 'Video uploaded successfully!',
      });
      setFile(null);
      // Reset the file input
      const fileInput = document.getElementById('video-file') as HTMLInputElement;
      if (fileInput) {
        fileInput.value = '';
      }
    } catch (error: any) {
      setUploadStatus({
        success: false,
        message: error.response?.data || 'Failed to upload video',
      });
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="video-upload">
      <h2>Upload Video</h2>
      <p>Upload a video file to convert it to MP3</p>
      
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="video-file">Select Video File:</label>
          <input
            type="file"
            id="video-file"
            accept="video/*"
            onChange={handleFileChange}
            disabled={uploading}
          />
        </div>
        
        {file && (
          <div className="file-info">
            <p>Selected file: {file.name}</p>
            <p>Size: {(file.size / (1024 * 1024)).toFixed(2)} MB</p>
          </div>
        )}
        
        <button type="submit" disabled={!file || uploading}>
          {uploading ? 'Uploading...' : 'Upload Video'}
        </button>
        
        {uploadStatus && (
          <div className={`upload-status ${uploadStatus.success ? 'success' : 'error'}`}>
            {uploadStatus.message}
          </div>
        )}
      </form>
    </div>
  );
};

export default VideoUpload;