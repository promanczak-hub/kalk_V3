const fs = require('fs');
const path = require('path');

const srcDir = path.join(__dirname, 'frontend', 'src');

function walkDir(dir, callback) {
  fs.readdirSync(dir).forEach(f => {
    let dirPath = path.join(dir, f);
    let isDirectory = fs.statSync(dirPath).isDirectory();
    isDirectory ? walkDir(dirPath, callback) : callback(path.join(dir, f));
  });
}

let modifiedFiles = 0;

walkDir(srcDir, function(filePath) {
  if (filePath.endsWith('.ts') || filePath.endsWith('.tsx')) {
    let content = fs.readFileSync(filePath, 'utf8');
    let original = content;

    // Skip our library files
    if (filePath.includes('apiClient.ts') || filePath.includes('api.ts') || filePath.includes('payloadBuilders.ts')) return;

    let needsApiClientImport = false;

    // 1. Replace apiFetch -> apiClient.fetch
    if (content.includes('apiFetch')) {
      content = content.replace(/apiFetch\(/g, 'apiClient.fetch(');
      
      // Update import
      content = content.replace(/import\s*\{\s*apiFetch\s*\}\s*from\s*['"]([^'"]+)['"]/g, (match, p1) => {
        return `import { apiClient } from '${p1.replace(/\/api$/, '/apiClient')}'`;
      });
      needsApiClientImport = true;
    }

    // 2. Replace raw fetch -> apiClient.fetch (when fetching our API)
    // Looking for fetch(something/api/) or fetch(API_BASE_URL)
    const fetchRegex = /fetch\(([^)]*)\)/g;
    content = content.replace(fetchRegex, (match, p1) => {
      // Avoid replacing if it's already apiClient.fetch
      // Wait, regex above matches fetch(...) but it could be preceded by a dot.
      // So let's use a negative lookbehind (not supported in all node versions, but works in 10+)
      return match; // We'll do it via a safer regex
    });
    
    // Safer regex for fetch: \b但 not preceded by a dot
    const safeFetchRegex = /(?<!\.)\bfetch\(/g;
    if (content.match(safeFetchRegex)) {
      // Check if the file seems to make API calls to our backend.
      // E.g., uses API_BASE_URL, baseUrl, "/api", "http://localhost:8000"
      if (content.includes('API_BASE_URL') || content.includes('baseUrl') || content.includes('"/api') || content.includes('`/api')) {
        content = content.replace(safeFetchRegex, 'apiClient.fetch(');
        needsApiClientImport = true;
      }
    }

    // If we changed to apiClient.fetch but didn't have the import (because it was just fetch)
    if (needsApiClientImport && !content.includes('import { apiClient }')) {
      // We need to add the import. Figure out relative path to `frontend/src/lib/apiClient`
      const relativeLevels = path.relative(path.dirname(filePath), path.join(srcDir, 'lib')).split(path.sep).join('/');
      let importPath = relativeLevels.startsWith('.') ? relativeLevels : `./${relativeLevels}`;
      if (importPath === '.') importPath = './lib'; // if it's in src
      
      const importStatement = `import { apiClient } from "${importPath}/apiClient";\n`;
      
      // Insert after the last import, or at the top
      const lastImportIndex = content.lastIndexOf('import ');
      if (lastImportIndex !== -1) {
        const endOfLine = content.indexOf('\n', lastImportIndex);
        content = content.slice(0, endOfLine + 1) + importStatement + content.slice(endOfLine + 1);
      } else {
        content = importStatement + content;
      }
    }

    if (original !== content) {
      fs.writeFileSync(filePath, content);
      modifiedFiles++;
      console.log(`Updated: ${path.relative(__dirname, filePath)}`);
    }
  }
});

console.log(`\nModified ${modifiedFiles} files.`);
