const express = require('express');
const bodyParser = require('body-parser');
const fs = require('fs');
const path = require('path');
const { exec } = require('child_process');
const http = require('http');

const app = express();
const PORT = process.env.PORT || 3000;

// Track completion status
let isComplete = false;
let totalSaved = 0;
let totalSkipped = 0;

// Parse JSON bodies
app.use(bodyParser.json({ limit: '50mb' }));
app.use(express.static(__dirname));

// Get directories from environment variables
const audioFile = process.env.AUDIO_FILE;
const reverbDir = process.env.REVERB_DIR;
const outputDir = process.env.OUTPUT_DIR;

// Serve audio files
app.use('/audio', express.static(path.dirname(audioFile)));
app.use('/reverb', express.static(path.resolve(__dirname, reverbDir)));

// Serve the HTML file
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'process_with_data.html'));
});

// Endpoint to check if a file already exists
app.get('/check-file', (req, res) => {
  const { id } = req.query;

  if (!id) {
    return res.status(400).json({ error: 'Missing id parameter' });
  }

  const filePath = path.join(outputDir, `${id}.wav`);
  const exists = fs.existsSync(filePath);

  if (exists) {
    totalSkipped++;
    console.log(`File already exists: ${filePath} (skipped)`);
  }

  res.json({ exists });
});

// Endpoint to save processed audio
app.post('/save', (req, res) => {
  const { id, data } = req.body;

  if (!id || !data) {
    return res.status(400).json({ error: 'Missing id or data' });
  }

  // Convert base64 to buffer
  const buffer = Buffer.from(data, 'base64');

  // Ensure directory exists
  const dirPath = path.dirname(path.join(outputDir, `${id}.wav`));
  if (!fs.existsSync(dirPath)) {
    fs.mkdirSync(dirPath, { recursive: true });
  }

  // Save file
  const filePath = path.join(outputDir, `${id}.wav`);
  fs.writeFileSync(filePath, buffer);

  // Create corresponding reverb info JSON file
  const reverbId = id.split('_').pop();
  const reverbInfoPath = path.join(outputDir, `${id}_reverb_info.json`);

  // Find the matching reverb file in the reverb directory
  const reverbSourcePath = path.join(reverbDir, `reverb_${reverbId}.json`);

  if (fs.existsSync(reverbSourcePath)) {
    fs.copyFileSync(reverbSourcePath, reverbInfoPath);
  }

  totalSaved++;
  console.log(`Saved ${filePath} (${totalSaved} files processed, ${totalSkipped} files skipped)`);

  res.json({ success: true, path: filePath });
});

// Endpoint to signal processing completion
app.post('/complete', (req, res) => {
  isComplete = true;
  console.log('Processing complete! All audio files have been processed.');
  console.log(`총 ${totalSaved}개의 리버브 이펙트가 적용되어 저장되었습니다.`);
  console.log(`총 ${totalSkipped}개의 파일이 이미 존재하여 건너뛰었습니다.`);
  res.json({ success: true });

  // Wait 2 seconds then exit process to allow for clean shutdown
  setTimeout(() => {
    console.log('Auto-shutting down server...');
    process.exit(0);
  }, 2000);
});

// Start server
const server = app.listen(PORT, () => {
  console.log(`Server running at http://localhost:${PORT}`);
  console.log(`Audio file: ${audioFile}`);
  console.log(`Reverb directory: ${path.resolve(__dirname, reverbDir)}`);
  console.log(`Output directory: ${path.resolve(__dirname, outputDir)}`);

  // Auto-open the browser (works on most systems)
  console.log('Attempting to open browser automatically...');
  let command;
  switch (process.platform) {
    case 'darwin': // macOS
      command = `open http://localhost:${PORT}`;
      break;
    case 'win32': // Windows
      command = `start http://localhost:${PORT}`;
      break;
    default: // Linux and others
      command = `xdg-open http://localhost:${PORT}`;
  }

  exec(command, (error) => {
    if (error) {
      console.log('Failed to open browser automatically. Please open manually.');
    }
  });
});

// Add a timeout to auto-shutdown the server if processing doesn't complete
const TIMEOUT_MINUTES = 30;
setTimeout(() => {
  if (!isComplete) {
    console.log(`Timeout after ${TIMEOUT_MINUTES} minutes. Shutting down server.`);
    server.close();
    process.exit(1);
  }
}, TIMEOUT_MINUTES * 60 * 1000);
