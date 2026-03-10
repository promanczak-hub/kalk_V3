import fs from 'fs';
import path from 'path';

const file = path.join(process.cwd(), 'src/components/CalculatorSections/VehicleDataSection.tsx');
let content = fs.readFileSync(file, 'utf8');

// Replace <Grid ... xs={X} sm={Y} md={Z} ...> -> <Grid ... size={{ xs: X, sm: Y, md: Z }} ...>
// First, we know from earlier run that we removed `item `. If not, we'd remove `item `.
// Let's replace any `xs={val}`, `sm={val}`, `md={val}` with size object.
content = content.replace(/<(Grid.*?)(xs={(\d+)}|sm={(\d+)}|md={(\d+)})(.*?)/g, (match, prefix, p2, p3, p4, p5, suffix) => {
    // wait, regex replace is hard to get right this way.
    return match;
});

// A simpler way:
const lines = content.split('\n');
const fixedLines = lines.map(line => {
    if (line.includes('<Grid')) {
        let sizeProps = [];
        let newLine = line.replace(/\bitem\b/, ''); // remove any `item` if still there
        
        const xsMatch = newLine.match(/xs={(\d+)}/);
        if (xsMatch) sizeProps.push(`xs: ${xsMatch[1]}`);
        
        const smMatch = newLine.match(/sm={(\d+)}/);
        if (smMatch) sizeProps.push(`sm: ${smMatch[1]}`);
        
        const mdMatch = newLine.match(/md={(\d+)}/);
        if (mdMatch) sizeProps.push(`md: ${mdMatch[1]}`);
        
        if (sizeProps.length > 0) {
            newLine = newLine.replace(/xs={(\d+)}/, '');
            newLine = newLine.replace(/sm={(\d+)}/, '');
            newLine = newLine.replace(/md={(\d+)}/, '');
            newLine = newLine.replace(/>/g, ''); // temporarily removing >
            
            // Re-add the closing bracket, and also insert size
            newLine = newLine.trim() + ` size={{ ${sizeProps.join(', ')} }}>`;
            
            // cleanup double spaces
            newLine = newLine.replace(/\s+/g, ' ').replace(' >', '>');
        }
        return newLine;
    }
    return line;
});

fs.writeFileSync(file, fixedLines.join('\n'));
console.log('Fixed Grid migration');
