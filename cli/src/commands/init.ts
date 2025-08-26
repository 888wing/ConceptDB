import { Command } from 'commander';
import chalk from 'chalk';
import inquirer from 'inquirer';
import fs from 'fs';
import path from 'path';

export const initCommand = new Command('init')
  .description('Initialize a new ConceptDB project')
  .argument('[name]', 'Project name')
  .action(async (name?: string) => {
    console.log(chalk.cyan('🚀 Initializing ConceptDB project...'));
    
    const answers = await inquirer.prompt([
      {
        type: 'input',
        name: 'projectName',
        message: 'Project name:',
        default: name || 'my-conceptdb-app',
        validate: (input: string) => input.length > 0
      },
      {
        type: 'list',
        name: 'phase',
        message: 'Select evolution phase:',
        choices: [
          { name: 'Phase 1 (10% concepts)', value: 1 },
          { name: 'Phase 2 (30% concepts)', value: 2 },
          { name: 'Phase 3 (70% concepts)', value: 3 },
          { name: 'Phase 4 (100% concepts)', value: 4 }
        ],
        default: 0
      },
      {
        type: 'confirm',
        name: 'useDocker',
        message: 'Use Docker for services?',
        default: true
      }
    ]);
    
    const projectDir = path.join(process.cwd(), answers.projectName);
    
    // Create project directory
    if (!fs.existsSync(projectDir)) {
      fs.mkdirSync(projectDir, { recursive: true });
    }
    
    // Create .env file
    const envContent = `
# ConceptDB Configuration
CONCEPTDB_HOST=localhost
CONCEPTDB_PORT=8000
POSTGRES_HOST=localhost
POSTGRES_PORT=5433
POSTGRES_DB=conceptdb
POSTGRES_USER=concept_user
POSTGRES_PASSWORD=concept_pass
QDRANT_HOST=localhost
QDRANT_PORT=6333
EVOLUTION_PHASE=${answers.phase}
CONCEPT_RATIO=${answers.phase === 1 ? 0.1 : answers.phase === 2 ? 0.3 : answers.phase === 3 ? 0.7 : 1.0}
`.trim();
    
    fs.writeFileSync(path.join(projectDir, '.env'), envContent);
    
    // Create docker-compose.yml if needed
    if (answers.useDocker) {
      const dockerContent = `
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    ports:
      - "5433:5432"
    environment:
      POSTGRES_DB: conceptdb
      POSTGRES_USER: concept_user
      POSTGRES_PASSWORD: concept_pass
    volumes:
      - postgres_data:/var/lib/postgresql/data

  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage

volumes:
  postgres_data:
  qdrant_data:
`.trim();
      
      fs.writeFileSync(path.join(projectDir, 'docker-compose.yml'), dockerContent);
    }
    
    console.log(chalk.green('\n✅ Project initialized successfully!'));
    console.log(chalk.cyan('\nNext steps:'));
    console.log(`  1. cd ${answers.projectName}`);
    if (answers.useDocker) {
      console.log('  2. docker-compose up -d');
    }
    console.log('  3. conceptdb dev');
  });
