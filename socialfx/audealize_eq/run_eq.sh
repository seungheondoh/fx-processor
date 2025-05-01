#!/bin/bash

# Script to apply EQ effects to a single audio file using Equalizer.js via Web Audio API
# Usage: ./run_eq.sh [PORT] [INSTRUMENT]

# Define paths with absolute paths
AUDIO_DIR="/workspace/fx-processor/socialfx/data/audio"
EQ_DIR="/workspace/fx-processor/socialfx/data/json/eq"
OUTPUT_DIR="/workspace/fx-processor/socialfx/data/fx_audio/eq"

# Default port
PORT=3000

# Default instrument
INSTRUMENT="drums"

# Check if port is provided as an argument
if [ $# -gt 0 ]; then
  PORT=$1
fi

# Check if instrument is provided as an argument
if [ $# -gt 1 ]; then
  INSTRUMENT=$2
fi

# Validate instrument selection
if [[ ! "$INSTRUMENT" =~ ^(drums|piano|guitar)$ ]]; then
  echo "Invalid instrument selection: $INSTRUMENT"
  echo "Please choose from: drums, piano, guitar"
  echo "Using default: drums"
  INSTRUMENT="drums"
fi

# Set the specific audio file to process
AUDIO_FILE="$AUDIO_DIR/$INSTRUMENT.wav"
echo "Selected instrument: $INSTRUMENT"
echo "Using audio file: $AUDIO_FILE"

# Check if the audio file exists
if [ ! -f "$AUDIO_FILE" ]; then
  echo "Error: Audio file $AUDIO_FILE does not exist"
  exit 1
fi

# Create output directory if it doesn't exist
mkdir -p $OUTPUT_DIR

# Prepare for the HTML method
HTML_DIR="./html_processor"
mkdir -p $HTML_DIR

# Copy the equalizer.js file
cp static/js/effects/equalizer.js $HTML_DIR/

# Create HTML file for processing audio
cat > $HTML_DIR/process_audio.html << 'EOF'
<!DOCTYPE html>
<html>
<head>
  <title>Audio EQ Processor</title>
  <script src="equalizer.js"></script>
  <script>
    // Store processed audio files
    let processedBuffers = {};
    let totalJobs = 0;
    let completedJobs = 0;

    // Main audio processing function
    async function processAudio(audioPath, eqParams, outputId) {
      return new Promise((resolve, reject) => {
        try {
          const context = new (window.AudioContext || window.webkitAudioContext)();

          // Load audio file
          fetch(audioPath)
            .then(response => {
              if (!response.ok) {
                throw new Error(`Failed to fetch audio file: ${audioPath} (${response.status})`);
              }
              return response.arrayBuffer();
            })
            .then(arrayBuffer => context.decodeAudioData(arrayBuffer))
            .then(audioBuffer => {
              // Create offline context for rendering
              const offlineContext = new OfflineAudioContext(
                audioBuffer.numberOfChannels,
                audioBuffer.length,
                audioBuffer.sampleRate
              );

              // Create source node
              const source = offlineContext.createBufferSource();
              source.buffer = audioBuffer;

              // Create equalizer with params
              const eq = new Equalizer(offlineContext, { curve: eqParams });

              // Connect audio nodes
              source.connect(eq.input);
              eq.connect(offlineContext.destination);

              // Start processing and render
              source.start(0);
              offlineContext.startRendering()
                .then(renderedBuffer => {
                  // Convert to WAV format
                  const wavData = bufferToWave(renderedBuffer);

                  // Store processed buffer
                  processedBuffers[outputId] = wavData;

                  // Save to server
                  saveToServer(wavData, outputId);

                  // Update progress
                  completedJobs++;
                  updateProgress();

                  resolve();
                })
                .catch(error => {
                  console.error('Rendering error:', error);
                  reject(error);
                });
            })
            .catch(error => {
              console.error('Audio loading error:', error);
              document.getElementById('error-log').innerHTML += `<div>Error loading: ${audioPath} - ${error.message}</div>`;
              reject(error);
            });
        } catch (error) {
          console.error('Processing error:', error);
          reject(error);
        }
      });
    }

    // Convert AudioBuffer to WAV format
    function bufferToWave(abuffer) {
      const numOfChan = abuffer.numberOfChannels;
      const length = abuffer.length * numOfChan * 2;
      const buffer = new ArrayBuffer(44 + length);
      const view = new DataView(buffer);

      // Write WAV header
      writeString(view, 0, 'RIFF');
      view.setUint32(4, 36 + length, true);
      writeString(view, 8, 'WAVE');
      writeString(view, 12, 'fmt ');
      view.setUint32(16, 16, true);
      view.setUint16(20, 1, true);
      view.setUint16(22, numOfChan, true);
      view.setUint32(24, abuffer.sampleRate, true);
      view.setUint32(28, abuffer.sampleRate * 2 * numOfChan, true);
      view.setUint16(32, numOfChan * 2, true);
      view.setUint16(34, 16, true);
      writeString(view, 36, 'data');
      view.setUint32(40, length, true);

      // Write audio data
      const offset = 44;
      for (let i = 0; i < abuffer.numberOfChannels; i++) {
        const channelData = abuffer.getChannelData(i);
        for (let j = 0; j < abuffer.length; j++) {
          const index = offset + (j * numOfChan + i) * 2;
          const sample = Math.max(-1, Math.min(1, channelData[j]));
          view.setInt16(index, sample < 0 ? sample * 0x8000 : sample * 0x7FFF, true);
        }
      }

      return buffer;
    }

    function writeString(view, offset, string) {
      for (let i = 0; i < string.length; i++) {
        view.setUint8(offset + i, string.charCodeAt(i));
      }
    }

    // Save processed audio to server
    function saveToServer(audioData, outputId) {
      // Convert array buffer to base64 string
      const blob = new Blob([audioData], { type: 'audio/wav' });
      const reader = new FileReader();

      reader.onloadend = function() {
        const base64data = reader.result.split(',')[1];

        // Send to server
        fetch('/save', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            id: outputId,
            data: base64data
          })
        })
        .then(response => response.json())
        .then(data => {
          console.log('Server saved:', data);
          // Check if all jobs are complete
          if (completedJobs >= totalJobs) {
            document.getElementById('complete-message').style.display = 'block';
            // Signal completion to the automation
            fetch('/complete', { method: 'POST' });
          }
        })
        .catch(error => {
          console.error('Save error:', error);
        });
      };

      reader.readAsDataURL(blob);
    }

    // Update progress bar and status
    function updateProgress() {
      const percent = Math.floor((completedJobs / totalJobs) * 100);
      document.getElementById('progress-bar').style.width = percent + '%';
      document.getElementById('status').textContent =
        `Processing: ${completedJobs} of ${totalJobs} complete (${percent}%)`;
    }

    // Process a batch of audio files
    async function processBatch(batchData) {
      totalJobs = batchData.length;
      completedJobs = 0;

      document.getElementById('status').textContent = 'Starting batch processing...';
      updateProgress();

      // Process files in parallel, but in small batches to avoid memory issues
      const batchSize = 16; // Process 5 files at a time
      for (let i = 0; i < batchData.length; i += batchSize) {
        const batch = batchData.slice(i, i + batchSize);
        await Promise.all(batch.map(job => processAudio(job.audioFile, job.eqParams, job.outputId)));
      }
    }

    // Initialize processing when data is available
    window.onload = function() {
      // Check if we have processing data
      if (window.processingData) {
        processBatch(window.processingData);
      }
    };
  </script>
</head>
<body>
  <h1>Audio EQ Processor</h1>
  <div id="status">Waiting for processing jobs...</div>
  <div id="progress-container">
    <div id="progress-bar"></div>
  </div>
  <div id="complete-message">
    <h3>Processing Complete!</h3>
    <p>All audio files have been processed and saved. You can now close this window.</p>
  </div>
  <div id="error-log"></div>
</body>
</html>
EOF

# Create a simple server to save files
cat > $HTML_DIR/server.js << 'EOF'
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
EOF

# Create script to prepare batch processing data
cat > $HTML_DIR/prepare_data.js << 'EOF'
const fs = require('fs');
const path = require('path');

// Get arguments
const audioFile = process.argv[2];
const eqDir = process.argv[3];
const outputDir = process.argv[4];
const serverUrl = process.argv[5] || 'http://localhost:3000';

// Verify audio file exists
if (!fs.existsSync(audioFile)) {
  console.error(`Error: Audio file ${audioFile} does not exist`);
  process.exit(1);
}

// Get audio file name
const audioName = path.basename(audioFile, '.wav');

// Get EQ settings
const eqFiles = fs.readdirSync(eqDir)
  .filter(file => file.endsWith('.json'));

// Create processing data
const processingData = [];
const skippedFiles = [];

for (const eqFile of eqFiles) {
  const eqId = path.basename(eqFile, '.json').split('_')[1];
  const eqPath = path.join(eqDir, eqFile);
  const eqData = JSON.parse(fs.readFileSync(eqPath, 'utf8'));

  // Check if this file already exists in the output directory
  const outputFilePath = path.join(outputDir, `eq_${eqId}/${audioName}.wav`);

  if (fs.existsSync(outputFilePath)) {
    skippedFiles.push(`eq_${eqId}/${audioName}.wav`);
    continue; // Skip this file as it already exists
  }

  processingData.push({
    // Use web server URL paths instead of filesystem paths
    audioFile: `/audio/${path.basename(audioFile)}`,
    eqId: eqId,
    eqParams: eqData.param_values,
    outputId: `eq_${eqId}/${audioName}`
  });
}

// Log skipped files
if (skippedFiles.length > 0) {
  console.log(`Skipping ${skippedFiles.length} already processed files:`);
  if (skippedFiles.length <= 10) {
    skippedFiles.forEach(file => console.log(`  - ${file}`));
  } else {
    skippedFiles.slice(0, 10).forEach(file => console.log(`  - ${file}`));
    console.log(`  ... and ${skippedFiles.length - 10} more`);
  }
}

// Create HTML with data
const htmlTemplate = fs.readFileSync(path.join(__dirname, 'process_audio.html'), 'utf8');
const htmlWithData = htmlTemplate.replace('</head>',
  `<script>
    window.processingData = ${JSON.stringify(processingData)};
    window.outputDir = "${outputDir}";
  </script>
</head>`
);

fs.writeFileSync(path.join(__dirname, 'process_with_data.html'), htmlWithData);

console.log(`Prepared data for ${processingData.length} processing jobs`);
console.log(`1. Start the server with: node server.js`);
console.log(`2. Open in browser: ${serverUrl}`);
console.log(`3. Files will be saved to: ${outputDir}`);
EOF

echo "Setting up HTML-based audio processing..."

# Kill any existing Node.js process on port $PORT
echo "Stopping any existing server on port $PORT..."
if command -v lsof > /dev/null; then
  PORT_PID=$(lsof -t -i:$PORT 2>/dev/null)
  if [ -n "$PORT_PID" ]; then
    echo "Killing process $PORT_PID running on port $PORT..."
    kill -9 $PORT_PID 2>/dev/null
  fi
elif command -v fuser > /dev/null; then
  fuser -k $PORT/tcp 2>/dev/null
fi

# Make sure audio file exists
if [ ! -f "$AUDIO_FILE" ]; then
  echo "Error: Audio file $AUDIO_FILE does not exist"
  exit 1
fi

if [ ! -d "$EQ_DIR" ] || [ -z "$(ls -A $EQ_DIR 2>/dev/null)" ]; then
  echo "Error: EQ directory $EQ_DIR does not exist or is empty"
  exit 1
fi

# Print the audio file and EQ directories
echo "Using audio file: $AUDIO_FILE"
echo "EQ files in $EQ_DIR:"
ls -la "$EQ_DIR" | grep ".json" | head -5
if [ "$(ls -1 "$EQ_DIR" | grep ".json" | wc -l)" -gt 5 ]; then
  echo "...and $(( $(ls -1 "$EQ_DIR" | grep ".json" | wc -l) - 5 )) more"
fi

# Run the entire process automatically
echo "Running the entire audio processing pipeline..."

# Create output directories for each EQ preset
echo "Creating output directories for each EQ preset..."
for eq_file in "$EQ_DIR"/*.json; do
  eq_name=$(basename "$eq_file" .json)
  eq_dir="$OUTPUT_DIR/$eq_name"
  mkdir -p "$eq_dir"
done

# Prepare the processing data
echo "Preparing processing data..."
cd $HTML_DIR
export AUDIO_DIR="$(dirname "$AUDIO_FILE")"
export EQ_DIR="$EQ_DIR"
export OUTPUT_DIR="$OUTPUT_DIR"
export PORT="$PORT"
node prepare_data.js "$AUDIO_FILE" "$EQ_DIR" "$OUTPUT_DIR" "http://localhost:$PORT"

echo "Starting the server to process audio files automatically..."
# Start the server (not in background to see logs)
echo "Starting server with: node server.js"
node server.js
