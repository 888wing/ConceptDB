import { Command } from 'commander';
import chalk from 'chalk';
import ora from 'ora';
import fs from 'fs';
import path from 'path';
import csv from 'csv-parser';
import { ConceptDBClient } from '../utils/client';

export const importCommand = new Command('import')
  .description('Import data into ConceptDB')
  .argument('<file>', 'File to import (CSV, JSON, or TXT)')
  .option('-t, --type <type>', 'Data type (auto-detected if not specified)', 'auto')
  .option('-e, --extract-concepts', 'Automatically extract concepts from text data')
  .option('-m, --mapping <mapping>', 'Column mapping for concept extraction (JSON string)')
  .option('-b, --batch-size <size>', 'Batch size for import', '100')
  .action(async (file: string, options: any) => {
    const spinner = ora('Preparing import...').start();
    
    try {
      // Check if file exists
      const filePath = path.resolve(file);
      if (!fs.existsSync(filePath)) {
        spinner.fail(`File not found: ${file}`);
        process.exit(1);
      }
      
      const client = new ConceptDBClient();
      const fileExt = path.extname(filePath).toLowerCase();
      const batchSize = parseInt(options.batchSize);
      
      // Detect file type
      let dataType = options.type;
      if (dataType === 'auto') {
        if (fileExt === '.csv') dataType = 'csv';
        else if (fileExt === '.json') dataType = 'json';
        else if (fileExt === '.txt') dataType = 'text';
        else {
          spinner.fail('Could not detect file type. Please specify with --type');
          process.exit(1);
        }
      }
      
      spinner.text = `Importing ${dataType} data...`;
      
      // Import based on type
      let records: any[] = [];
      let totalRecords = 0;
      let importedRecords = 0;
      let extractedConcepts = 0;
      
      if (dataType === 'csv') {
        // Parse CSV
        records = await parseCSV(filePath);
        totalRecords = records.length;
        
        spinner.text = `Importing ${totalRecords} records...`;
        
        // Import in batches
        for (let i = 0; i < records.length; i += batchSize) {
          const batch = records.slice(i, Math.min(i + batchSize, records.length));
          
          // Import to PostgreSQL layer
          const result = await client.importData({
            records: batch,
            source: file,
            type: 'structured'
          });
          
          importedRecords += result.imported;
          
          // Extract concepts if requested
          if (options.extractConcepts) {
            const mapping = options.mapping ? JSON.parse(options.mapping) : null;
            const conceptResult = await client.extractConcepts({
              records: batch,
              mapping: mapping,
              auto_detect: !mapping
            });
            
            extractedConcepts += conceptResult.concepts_created || 0;
          }
          
          spinner.text = `Imported ${importedRecords}/${totalRecords} records...`;
        }
        
      } else if (dataType === 'json') {
        // Parse JSON
        const content = fs.readFileSync(filePath, 'utf-8');
        records = JSON.parse(content);
        
        if (!Array.isArray(records)) {
          records = [records];
        }
        
        totalRecords = records.length;
        spinner.text = `Importing ${totalRecords} records...`;
        
        // Import in batches
        for (let i = 0; i < records.length; i += batchSize) {
          const batch = records.slice(i, Math.min(i + batchSize, records.length));
          
          const result = await client.importData({
            records: batch,
            source: file,
            type: 'structured'
          });
          
          importedRecords += result.imported;
          
          if (options.extractConcepts) {
            const conceptResult = await client.extractConcepts({
              records: batch,
              auto_detect: true
            });
            
            extractedConcepts += conceptResult.concepts_created || 0;
          }
          
          spinner.text = `Imported ${importedRecords}/${totalRecords} records...`;
        }
        
      } else if (dataType === 'text') {
        // Import text data
        const content = fs.readFileSync(filePath, 'utf-8');
        const lines = content.split('\n').filter(line => line.trim());
        
        totalRecords = 1; // Treat as single document
        spinner.text = 'Processing text document...';
        
        // Import as unstructured data
        const result = await client.importData({
          content: content,
          source: file,
          type: 'unstructured'
        });
        
        importedRecords = 1;
        
        // Always extract concepts from text
        const conceptResult = await client.extractConcepts({
          text: content,
          source: file
        });
        
        extractedConcepts = conceptResult.concepts_created || 0;
      }
      
      spinner.succeed('Import completed successfully');
      
      // Show results
      console.log('\n' + chalk.bold('📊 Import Summary'));
      console.log(chalk.gray('─'.repeat(50)));
      console.log(`File: ${chalk.cyan(file)}`);
      console.log(`Type: ${chalk.yellow(dataType)}`);
      console.log(`Records Imported: ${chalk.green(importedRecords)} / ${totalRecords}`);
      
      if (extractedConcepts > 0) {
        console.log(`Concepts Extracted: ${chalk.magenta(extractedConcepts)}`);
      }
      
      // Show evolution impact
      const metrics = await client.getEvolutionMetrics();
      const newRatio = metrics.conceptualization_ratio;
      console.log('\n' + chalk.bold('🧬 Evolution Impact'));
      console.log(chalk.gray('─'.repeat(50)));
      console.log(`Conceptualization: ${chalk.yellow((newRatio * 100).toFixed(1) + '%')}`);
      
      // Progress bar
      const progressLength = 40;
      const filledLength = Math.round(newRatio * progressLength);
      const progressBar = '█'.repeat(filledLength) + '░'.repeat(progressLength - filledLength);
      console.log(`[${progressBar}]`);
      
      // Suggest next steps
      console.log('\n' + chalk.bold('💡 Next Steps'));
      console.log(chalk.gray('─'.repeat(50)));
      console.log(`  • Query your data: ${chalk.cyan('conceptdb query "find patterns in the imported data"')}`);
      console.log(`  • View concepts: ${chalk.cyan('conceptdb concepts list')}`);
      console.log(`  • Check status: ${chalk.cyan('conceptdb status --verbose')}`);
      
    } catch (error: any) {
      spinner.fail('Import failed');
      console.error(chalk.red('Error:'), error.message);
      process.exit(1);
    }
  });

function parseCSV(filePath: string): Promise<any[]> {
  return new Promise((resolve, reject) => {
    const results: any[] = [];
    
    fs.createReadStream(filePath)
      .pipe(csv())
      .on('data', (data) => results.push(data))
      .on('end', () => resolve(results))
      .on('error', (error) => reject(error));
  });
}