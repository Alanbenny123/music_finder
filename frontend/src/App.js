import React, { useState } from 'react';
import {
  Box,
  Container,
  Typography,
  Paper,
  Button,
  CircularProgress,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  IconButton,
  Card,
  CardContent,
  Divider,
  Alert,
} from '@mui/material';
import {
  CloudUpload,
  MusicNote,
  Download,
  Album,
  Person,
  Category,
  LibraryMusic,
} from '@mui/icons-material';
import { styled } from '@mui/material/styles';
import axios from 'axios';

const Input = styled('input')({
  display: 'none',
});

const VisuallyHiddenInput = styled('input')({
  clip: 'rect(0 0 0 0)',
  clipPath: 'inset(50%)',
  height: 1,
  overflow: 'hidden',
  position: 'absolute',
  bottom: 0,
  left: 0,
  whiteSpace: 'nowrap',
  width: 1,
});

function App() {
  const [file, setFile] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [tracks, setTracks] = useState(null);
  const [musicInfo, setMusicInfo] = useState(null);
  const [error, setError] = useState(null);

  const handleFileChange = (event) => {
    const selectedFile = event.target.files[0];
    setFile(selectedFile);
    setError(null);
    setTracks(null);
    setMusicInfo(null);
  };

  const handleUpload = async () => {
    if (!file) {
      setError('Please select a file first');
      return;
    }

    setIsProcessing(true);
    setError(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      // First check if the server is healthy
      const healthCheck = await axios.get('http://localhost:5000/health');
      console.log('Server health check:', healthCheck.data);

      const response = await axios.post('http://localhost:5000/api/separate', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          console.log('Upload progress:', percentCompleted, '%');
        },
      });

      console.log('Server response:', response.data);
      setTracks(response.data.tracks);
      if (response.data.music_info) {
        setMusicInfo(response.data.music_info);
      }
    } catch (err) {
      console.error('Error details:', err);
      setError(
        err.response?.data?.error || 
        err.message || 
        'An error occurred during processing'
      );
    } finally {
      setIsProcessing(false);
    }
  };

  const handleDownload = async (url, sourceName) => {
    try {
      window.location.href = `http://localhost:5000${url}`;
    } catch (err) {
      console.error('Download error:', err);
      setError('Error downloading file');
    }
  };

  return (
    <Container maxWidth="md">
      <Box sx={{ my: 4 }}>
        <Typography variant="h3" component="h1" gutterBottom align="center">
          Music Source Separator
        </Typography>
        
        <Paper 
          elevation={3} 
          sx={{ 
            p: 4, 
            display: 'flex', 
            flexDirection: 'column', 
            alignItems: 'center',
            gap: 2,
            backgroundColor: '#f5f5f5'
          }}
        >
          <Box sx={{ width: '100%', textAlign: 'center' }}>
            <label htmlFor="contained-button-file">
              <Input
                accept="video/*,audio/*"
                id="contained-button-file"
                type="file"
                onChange={handleFileChange}
              />
              <Button
                variant="contained"
                component="span"
                startIcon={<CloudUpload />}
                sx={{ mb: 2 }}
              >
                Select File
              </Button>
            </label>
            
            {file && (
              <Typography variant="body1" sx={{ mt: 1 }}>
                Selected file: {file.name}
              </Typography>
            )}
          </Box>

          <Button
            variant="contained"
            color="primary"
            onClick={handleUpload}
            disabled={!file || isProcessing}
            sx={{ mt: 2 }}
          >
            {isProcessing ? 'Processing...' : 'Start Separation'}
          </Button>

          {isProcessing && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <CircularProgress />
              <Typography>Processing your file...</Typography>
            </Box>
          )}

          {error && (
            <Alert severity="error" sx={{ mt: 2, width: '100%' }}>
              {error}
            </Alert>
          )}

          {tracks && (
            <Box sx={{ width: '100%', mt: 2 }}>
              <Typography variant="h6" gutterBottom>
                Separated Tracks
              </Typography>
              <List>
                {Object.entries(tracks).map(([source, url]) => (
                  <ListItem key={source}>
                    <ListItemIcon>
                      <MusicNote />
                    </ListItemIcon>
                    <ListItemText primary={source.charAt(0).toUpperCase() + source.slice(1)} />
                    <IconButton
                      edge="end"
                      onClick={() => handleDownload(url, source)}
                      color="primary"
                    >
                      <Download />
                    </IconButton>
                  </ListItem>
                ))}
              </List>
            </Box>
          )}

          {musicInfo && (
            <Card sx={{ width: '100%', mt: 2, bgcolor: '#fff' }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Detected Music Information
                </Typography>
                <List>
                  <ListItem>
                    <ListItemIcon>
                      <LibraryMusic />
                    </ListItemIcon>
                    <ListItemText primary="Title" secondary={musicInfo.title} />
                  </ListItem>
                  <ListItem>
                    <ListItemIcon>
                      <Person />
                    </ListItemIcon>
                    <ListItemText primary="Artist" secondary={musicInfo.artist} />
                  </ListItem>
                  <ListItem>
                    <ListItemIcon>
                      <Category />
                    </ListItemIcon>
                    <ListItemText primary="Genre" secondary={musicInfo.genre} />
                  </ListItem>
                  <ListItem>
                    <ListItemIcon>
                      <Album />
                    </ListItemIcon>
                    <ListItemText primary="Album" secondary={musicInfo.album} />
                  </ListItem>
                </List>
              </CardContent>
            </Card>
          )}
        </Paper>
      </Box>
    </Container>
  );
}

export default App;
