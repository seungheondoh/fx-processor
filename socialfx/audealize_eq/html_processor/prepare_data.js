const fs = require('fs');
const path = require('path');

// Get arguments
const audioDir = process.argv[2];
const eqDir = process.argv[3];
const outputDir = process.argv[4];
const serverUrl = process.argv[5] || 'http://localhost:3000';

// Get audio files and EQ settings
const audioFiles = fs.readdirSync(audioDir)
  .filter(file => file.endsWith('.wav'))
  .map(file => path.join(audioDir, file));

const eqFiles = fs.readdirSync(eqDir)
  .filter(file => file.endsWith('.json'))

// Create processing data
const processingData = [];
const skippedFiles = [];

for (const audioFile of audioFiles) {
  const audioName = path.basename(audioFile, '.wav');

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

// Set environment variables for server
process.env.AUDIO_DIR = audioDir;
process.env.EQ_DIR = eqDir;
process.env.OUTPUT_DIR = outputDir;

console.log(`Prepared data for ${processingData.length} processing jobs`);
console.log(`1. Start the server with: node server.js`);
console.log(`2. Open in browser: ${serverUrl}`);
console.log(`3. Files will be saved to: ${outputDir}`);
