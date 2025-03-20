// JavaScript for handling file uploads and interactions
document.addEventListener('DOMContentLoaded', function () {
      const dropArea = document.getElementById('drop-area');
      const fileInput = document.getElementById('file-input');
      const selectFileBtn = document.getElementById('select-file');
  
      // Prevent default drag behaviors
      ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
          dropArea.addEventListener(eventName, preventDefaults, false);
      });
  
      // Highlight drop area when dragging over
      ['dragenter', 'dragover'].forEach(eventName => {
          dropArea.addEventListener(eventName, () => dropArea.classList.add('highlight'), false);
      });
  
      ['dragleave', 'drop'].forEach(eventName => {
          dropArea.addEventListener(eventName, () => dropArea.classList.remove('highlight'), false);
      });
  
      // Handle dropped files
      dropArea.addEventListener('drop', handleDrop, false);
  
      // Open file dialog when button is clicked
      selectFileBtn.addEventListener('click', () => fileInput.click());
  
      // Handle file selection
      fileInput.addEventListener('change', function () {
          handleFiles(this.files);
      });
  
      function preventDefaults(e) {
          e.preventDefault();
          e.stopPropagation();
      }
  
      function handleDrop(e) {
          const dt = e.dataTransfer;
          const files = dt.files;
          fileInput.files = files;
          handleFiles(files);
      }
  
      function handleFiles(files) {
          if (files.length > 0) {
              const fileName = files[0].name;
              dropArea.querySelector('p').textContent = `Selected file: ${fileName}`;
          }
      }
  });