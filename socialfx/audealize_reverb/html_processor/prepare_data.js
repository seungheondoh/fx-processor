const fs = require('fs');
const path = require('path');

// Get arguments
const audioFile = process.argv[2];
const reverbDir = process.argv[3];
const outputDir = process.argv[4];
const serverUrl = process.argv[5] || 'http://localhost:3000';

// Get audio file and reverb settings
const audioName = path.basename(audioFile, '.wav');

const reverbFiles = fs.readdirSync(reverbDir)
  .filter(file => file.endsWith('.json'))

// Create processing data
const processingData = [];

for (const reverbFile of reverbFiles) {
  const reverbId = path.basename(reverbFile, '.json').split('_')[1];
  const reverbPath = path.join(reverbDir, reverbFile);
  const reverbData = JSON.parse(fs.readFileSync(reverbPath, 'utf8'));

  processingData.push({
    // Use web server URL paths instead of filesystem paths
    audioFile: `/audio/${path.basename(audioFile)}`,
    reverbId: reverbId,
    reverbParams: reverbData.param_values,
    outputId: `reverb_${reverbId}/${audioName}`
  });
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

// Set environment variables for server
process.env.AUDIO_FILE = audioFile;
process.env.REVERB_DIR = reverbDir;
process.env.OUTPUT_DIR = outputDir;

console.log(`Prepared data for ${processingData.length} processing jobs`);
console.log(`1. Start the server with: node server.js`);
console.log(`2. Open in browser: ${serverUrl}`);
console.log(`3. Files will be saved to: ${outputDir}`);
