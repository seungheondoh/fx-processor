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

// Parse JSON bodies
app.use(bodyParser.json({ limit: '50mb' }));
app.use(express.static(__dirname));

// Get directories from environment variables
const audioDir = process.env.AUDIO_DIR;
const eqDir = process.env.EQ_DIR;
const outputDir = process.env.OUTPUT_DIR;

// Serve audio files
app.use('/audio', express.static(path.resolve(__dirname, audioDir)));
app.use('/eq', express.static(path.resolve(__dirname, eqDir)));

// Serve the HTML file
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'process_with_data.html'));
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
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }

  // Save file
  const filePath = path.join(outputDir, `${id}.wav`);
  fs.writeFileSync(filePath, buffer);

  // Create corresponding EQ info JSON file
  const eqId = id.split('_').pop();
  const eqInfoPath = path.join(outputDir, `${id}_eq_info.json`);

  // Find the matching EQ file in the EQ directory
  const eqSourcePath = path.join(eqDir, `eq_${eqId}.json`);

  if (fs.existsSync(eqSourcePath)) {
    fs.copyFileSync(eqSourcePath, eqInfoPath);
  }

  totalSaved++;
  console.log(`Saved ${filePath} (${totalSaved} files processed)`);

  res.json({ success: true, path: filePath });
});

// Endpoint to signal processing completion
app.post('/complete', (req, res) => {
  isComplete = true;
  console.log('Processing complete! All audio files have been processed.');
  console.log(`총 ${totalSaved}개의 이펙트가 적용되어 저장되었습니다.`);
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
  console.log(`Audio directory: ${path.resolve(__dirname, audioDir)}`);
  console.log(`EQ directory: ${path.resolve(__dirname, eqDir)}`);
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
