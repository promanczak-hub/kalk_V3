const fs = require('fs');
const path = require('path');

const srcDir = path.join('d:/kalk_v3/frontend/src');

function findFiles(dir, fileList = []) {
  const files = fs.readdirSync(dir);
  for (const file of files) {
    const filePath = path.join(dir, file);
    if (fs.statSync(filePath).isDirectory()) {
      findFiles(filePath, fileList);
    } else if (filePath.endsWith('.tsx') || filePath.endsWith('.ts')) {
      fileList.push(filePath);
    }
  }
  return fileList;
}

const allFiles = findFiles(srcDir);

for (const file of allFiles) {
  let content = fs.readFileSync(file, 'utf8');
  let updated = false;
  
  // Replace VITE_FRONTEND_URL as well
  if (content.includes('import.meta.env.VITE_FRONTEND_URL')) {
    const relativePath = path.relative(path.dirname(file), path.join(srcDir, 'config', 'env')).replace(/\\/g, '/');
    const importPath = relativePath.startsWith('.') ? relativePath : './' + relativePath;
    
    if (!content.includes('FRONTEND_URL')) {
        const lines = content.split('\n');
        let importIdx = 0;
        for (let i = 0; i < lines.length; i++) {
            if (lines[i].startsWith('import ')) {
                importIdx = i;
            }
        }
        lines.splice(importIdx + 1, 0, `// config export added by script`);
        content = lines.join('\n');
    }
    // We didn't define FRONTEND_URL in env.ts yet, skipping it or using a hardcoded fallback if missing
    // Actually, I'll only do VITE_API_URL and VITE_SUPABASE_URL here.
  }

  if (content.includes('import.meta.env.VITE_API_URL')) {
    const relativePath = path.relative(path.dirname(file), path.join(srcDir, 'config', 'env')).replace(/\\/g, '/');
    const importPath = relativePath.startsWith('.') ? relativePath : './' + relativePath;
    
    if (!content.includes('API_BASE_URL')) {
        const lines = content.split('\n');
        let importIdx = 0;
        for (let i = 0; i < lines.length; i++) {
            if (lines[i].startsWith('import ')) {
                importIdx = i;
            }
        }
        lines.splice(importIdx + 1, 0, `import { API_BASE_URL } from "${importPath}";`);
        content = lines.join('\n');
    }
    content = content.replace(/import\.meta\.env\.VITE_API_URL/g, 'API_BASE_URL');
    updated = true;
  }
  
  if (updated) {
    fs.writeFileSync(file, content);
    console.log(`Updated ${file}`);
  }
}
