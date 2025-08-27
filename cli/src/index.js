#!/usr/bin/env node

/**
 * ConceptDB CLI
 * Command-line interface for ConceptDB operations
 */

const { Command } = require('commander');
const chalk = require('chalk');
const ora = require('ora');
const Table = require('cli-table3');
const inquirer = require('inquirer');
const fs = require('fs-extra');
const path = require('path');
const axios = require('axios');
const dotenv = require('dotenv');

// Load environment variables
dotenv.config();

const program = new Command();
const API_URL = process.env.CONCEPTDB_URL || 'http://localhost:8000';

// Configure axios defaults
axios.defaults.baseURL = API_URL;
axios.defaults.headers.common['Content-Type'] = 'application/json';

// CLI version
const packageJson = require('../package.json');
program.version(packageJson.version);

/**
 * Initialize a new ConceptDB project
 */
program
  .command('init [project-name]')
  .description('Initialize a new ConceptDB project')
  .option('-t, --template <template>', 'Use a project template', 'default')
  .action(async (projectName, options) => {
    const spinner = ora('Initializing ConceptDB project...').start();
    
    try {
      // Prompt for project name if not provided
      if (!projectName) {
        const answers = await inquirer.prompt([
          {
            type: 'input',
            name: 'projectName',
            message: 'Project name:',
            default: 'my-conceptdb-project'
          }
        ]);
        projectName = answers.projectName;
      }
      
      const projectPath = path.join(process.cwd(), projectName);
      
      // Create project directory
      await fs.ensureDir(projectPath);
      
      // Create configuration file
      const config = {
        name: projectName,
        version: '1.0.0',
        conceptdb: {
          url: API_URL,
          phase: 1,
          conceptRatio: 0.1,
          features: {
            llm: false,
            autoExtraction: true,
            realTimeSync: false
          }
        },
        database: {
          postgres: {
            host: 'localhost',
            port: 5433,
            database: 'conceptdb',
            user: 'concept_user'
          },
          qdrant: {
            host: 'localhost',
            port: 6333
          }
        }
      };
      
      await fs.writeJson(
        path.join(projectPath, 'conceptdb.config.json'),
        config,
        { spaces: 2 }
      );
      
      // Create docker-compose file
      const dockerCompose = `version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: conceptdb
      POSTGRES_USER: concept_user
      POSTGRES_PASSWORD: concept_pass
    ports:
      - "5433:5432"
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
`;
      
      await fs.writeFile(
        path.join(projectPath, 'docker-compose.yml'),
        dockerCompose
      );
      
      // Create .env file
      const envContent = `# ConceptDB Configuration
CONCEPTDB_URL=http://localhost:8000
POSTGRES_URL=postgresql://concept_user:concept_pass@localhost:5433/conceptdb
QDRANT_URL=http://localhost:6333
OPENAI_API_KEY=your-api-key-here
`;
      
      await fs.writeFile(
        path.join(projectPath, '.env'),
        envContent
      );
      
      // Create example query file
      const exampleQueries = `# Example ConceptDB Queries

## SQL Queries (90% Path)
SELECT * FROM users WHERE age > 25;
SELECT COUNT(*) FROM products;

## Natural Language Queries (10% Path)
find customers who might churn
show me products similar to "laptop"
what concepts are related to user satisfaction

## Hybrid Queries
find users similar to our best customers where signup_date > '2023-01-01'
`;
      
      await fs.writeFile(
        path.join(projectPath, 'queries.md'),
        exampleQueries
      );
      
      spinner.succeed(chalk.green(`✓ ConceptDB project initialized at ${projectPath}`));
      
      console.log('\n' + chalk.cyan('Next steps:'));
      console.log(`  1. cd ${projectName}`);
      console.log('  2. docker-compose up -d');
      console.log('  3. conceptdb dev');
      
    } catch (error) {
      spinner.fail(chalk.red('Failed to initialize project'));
      console.error(error);
      process.exit(1);
    }
  });

/**
 * Start development server
 */
program
  .command('dev')
  .description('Start ConceptDB development server')
  .option('-p, --port <port>', 'Port to run on', '8000')
  .option('-d, --detached', 'Run in background')
  .action(async (options) => {
    const spinner = ora('Starting ConceptDB development server...').start();
    
    try {
      // Check if services are running
      const health = await checkHealth();
      
      if (!health.healthy) {
        spinner.warn(chalk.yellow('Services not running. Starting docker-compose...'));
        
        const { spawn } = require('child_process');
        const docker = spawn('docker-compose', ['up', '-d'], {
          stdio: options.detached ? 'ignore' : 'inherit'
        });
        
        await new Promise((resolve) => {
          docker.on('close', resolve);
        });
        
        // Wait for services to be ready
        await waitForServices();
      }
      
      spinner.succeed(chalk.green('✓ ConceptDB is running'));
      
      // Display service URLs
      const table = new Table({
        head: ['Service', 'URL', 'Status'],
        style: { head: ['cyan'] }
      });
      
      table.push(
        ['API', `http://localhost:${options.port}`, '✓ Running'],
        ['PostgreSQL', 'localhost:5433', '✓ Running'],
        ['Qdrant', 'localhost:6333', '✓ Running'],
        ['Web Studio', 'http://localhost:3000', '✓ Running']
      );
      
      console.log('\n' + table.toString());
      
      if (!options.detached) {
        console.log('\n' + chalk.gray('Press Ctrl+C to stop'));
        
        // Keep process alive
        process.stdin.resume();
        process.on('SIGINT', async () => {
          console.log('\n' + chalk.yellow('Shutting down...'));
          process.exit(0);
        });
      }
      
    } catch (error) {
      spinner.fail(chalk.red('Failed to start development server'));
      console.error(error);
      process.exit(1);
    }
  });

/**
 * Execute a query
 */
program
  .command('query <query>')
  .description('Execute a query against ConceptDB')
  .option('-t, --type <type>', 'Query type (sql/natural/auto)', 'auto')
  .option('-l, --limit <limit>', 'Limit results', '10')
  .option('-f, --format <format>', 'Output format (table/json)', 'table')
  .action(async (query, options) => {
    const spinner = ora('Executing query...').start();
    
    try {
      const response = await axios.post('/api/v1/query', {
        query,
        limit: parseInt(options.limit)
      });
      
      spinner.stop();
      
      const result = response.data;
      
      if (result.success) {
        // Display routing information
        console.log(chalk.cyan('\n📊 Query Analysis:'));
        console.log(`  Route: ${chalk.yellow(result.data.route)}`);
        console.log(`  Type: ${result.data.query_type}`);
        console.log(`  Confidence: ${result.data.confidence.toFixed(2)}`);
        console.log(`  Explanation: ${result.data.explanation}`);
        
        // Display results
        if (options.format === 'json') {
          console.log('\n' + JSON.stringify(result.data.results, null, 2));
        } else {
          displayResultsTable(result.data.results);
        }
      } else {
        console.error(chalk.red('Query failed:'), result.message);
      }
      
    } catch (error) {
      spinner.fail(chalk.red('Query execution failed'));
      console.error(error.message);
      process.exit(1);
    }
  });

/**
 * Import data from file
 */
program
  .command('import <file>')
  .description('Import data into ConceptDB')
  .option('-t, --table <table>', 'Target table name')
  .option('-e, --extract', 'Extract concepts automatically')
  .action(async (file, options) => {
    const spinner = ora('Importing data...').start();
    
    try {
      const data = await fs.readJson(file);
      
      if (!options.table) {
        const answers = await inquirer.prompt([
          {
            type: 'input',
            name: 'table',
            message: 'Target table name:',
            default: 'imported_data'
          }
        ]);
        options.table = answers.table;
      }
      
      // Import data
      let imported = 0;
      for (const row of data) {
        await axios.post('/api/v1/data', {
          table: options.table,
          data: row
        });
        imported++;
        spinner.text = `Importing... ${imported}/${data.length}`;
      }
      
      spinner.succeed(chalk.green(`✓ Imported ${imported} records`));
      
      // Extract concepts if requested
      if (options.extract) {
        spinner.start('Extracting concepts...');
        
        const extractResponse = await axios.post('/api/v1/concepts/extract', {
          table: options.table
        });
        
        if (extractResponse.data.success) {
          spinner.succeed(chalk.green(
            `✓ Extracted ${extractResponse.data.concepts_count} concepts`
          ));
        }
      }
      
    } catch (error) {
      spinner.fail(chalk.red('Import failed'));
      console.error(error.message);
      process.exit(1);
    }
  });

/**
 * Manage concepts
 */
program
  .command('concepts')
  .description('Manage concepts')
  .option('-l, --list', 'List all concepts')
  .option('-s, --search <query>', 'Search concepts')
  .option('-c, --create', 'Create a new concept')
  .option('-g, --graph', 'Show concept graph')
  .action(async (options) => {
    try {
      if (options.list) {
        const spinner = ora('Fetching concepts...').start();
        const response = await axios.get('/api/v1/concepts');
        spinner.stop();
        
        displayConceptsTable(response.data.concepts);
        
      } else if (options.search) {
        const spinner = ora('Searching concepts...').start();
        const response = await axios.post('/api/v1/concepts/search', {
          query: options.search,
          limit: 20
        });
        spinner.stop();
        
        displayConceptsTable(response.data.data.results);
        
      } else if (options.create) {
        const answers = await inquirer.prompt([
          {
            type: 'input',
            name: 'name',
            message: 'Concept name:'
          },
          {
            type: 'input',
            name: 'description',
            message: 'Description:'
          },
          {
            type: 'list',
            name: 'type',
            message: 'Type:',
            choices: ['general', 'entity', 'relationship', 'attribute']
          }
        ]);
        
        const spinner = ora('Creating concept...').start();
        const response = await axios.post('/api/v1/concepts', answers);
        
        if (response.data.success) {
          spinner.succeed(chalk.green('✓ Concept created'));
          console.log(response.data.data);
        } else {
          spinner.fail(chalk.red('Failed to create concept'));
        }
        
      } else if (options.graph) {
        const spinner = ora('Fetching concept graph...').start();
        const response = await axios.get('/api/v1/concepts/graph');
        spinner.stop();
        
        console.log(chalk.cyan('\n🌐 Concept Graph:'));
        console.log(`  Nodes: ${response.data.data.nodes.length}`);
        console.log(`  Edges: ${response.data.data.edges.length}`);
        console.log('\n  View in Web Studio: http://localhost:3000/graph');
      }
      
    } catch (error) {
      console.error(chalk.red('Error:'), error.message);
      process.exit(1);
    }
  });

/**
 * Show evolution metrics
 */
program
  .command('evolution')
  .description('Show evolution metrics and progress')
  .option('-e, --evolve', 'Trigger evolution to next phase')
  .action(async (options) => {
    try {
      if (options.evolve) {
        const confirm = await inquirer.prompt([
          {
            type: 'confirm',
            name: 'proceed',
            message: 'Are you sure you want to evolve to the next phase?',
            default: false
          }
        ]);
        
        if (confirm.proceed) {
          const spinner = ora('Triggering evolution...').start();
          const response = await axios.post('/api/v1/evolve');
          
          if (response.data.success) {
            spinner.succeed(chalk.green(response.data.message));
          } else {
            spinner.fail(chalk.yellow(response.data.message));
          }
        }
        
      } else {
        const spinner = ora('Fetching evolution metrics...').start();
        const response = await axios.get('/api/v1/metrics/evolution');
        spinner.stop();
        
        const metrics = response.data.data;
        
        console.log(chalk.cyan('\n📈 Evolution Metrics:'));
        console.log(`  Current Phase: ${chalk.yellow(metrics.current_phase)}`);
        console.log(`  Conceptualization: ${chalk.green(metrics.concept_percentage + '%')}`);
        console.log(`  Total Queries: ${metrics.total_queries}`);
        console.log(`  SQL Queries: ${metrics.sql_queries}`);
        console.log(`  Concept Queries: ${metrics.concept_queries}`);
        console.log(`  Hybrid Queries: ${metrics.hybrid_queries}`);
        
        // Progress bar
        const progress = Math.round(metrics.concept_percentage / 2.5); // 40 chars max
        const progressBar = '█'.repeat(progress) + '░'.repeat(40 - progress);
        console.log(`\n  Progress: [${progressBar}] ${metrics.concept_percentage}%`);
        
        if (metrics.next_phase_ready) {
          console.log('\n' + chalk.green('✓ ' + metrics.recommended_action));
        } else {
          console.log('\n' + chalk.yellow('→ ' + metrics.recommended_action));
        }
      }
      
    } catch (error) {
      console.error(chalk.red('Error:'), error.message);
      process.exit(1);
    }
  });

// Helper functions

async function checkHealth() {
  try {
    const response = await axios.get('/health');
    return {
      healthy: response.data.status === 'healthy',
      services: response.data.services
    };
  } catch (error) {
    return {
      healthy: false,
      services: {}
    };
  }
}

async function waitForServices(maxRetries = 30) {
  for (let i = 0; i < maxRetries; i++) {
    const health = await checkHealth();
    if (health.healthy) {
      return true;
    }
    await new Promise(resolve => setTimeout(resolve, 2000));
  }
  throw new Error('Services failed to start');
}

function displayResultsTable(results) {
  if (!results || results.length === 0) {
    console.log(chalk.yellow('\nNo results found'));
    return;
  }
  
  const table = new Table({
    head: Object.keys(results[0]),
    style: { head: ['cyan'] }
  });
  
  results.slice(0, 10).forEach(row => {
    table.push(Object.values(row).map(v => 
      v === null ? 'null' : 
      typeof v === 'object' ? JSON.stringify(v) : 
      String(v)
    ));
  });
  
  console.log('\n' + table.toString());
  
  if (results.length > 10) {
    console.log(chalk.gray(`\n... and ${results.length - 10} more results`));
  }
}

function displayConceptsTable(concepts) {
  if (!concepts || concepts.length === 0) {
    console.log(chalk.yellow('\nNo concepts found'));
    return;
  }
  
  const table = new Table({
    head: ['Name', 'Type', 'Confidence', 'Usage'],
    style: { head: ['cyan'] }
  });
  
  concepts.forEach(concept => {
    table.push([
      concept.name || concept.data?.name || '-',
      concept.type || concept.data?.type || 'general',
      concept.confidence?.toFixed(2) || concept.score?.toFixed(2) || '-',
      concept.usage_count || concept.data?.usage_count || 0
    ]);
  });
  
  console.log('\n' + table.toString());
}

// Parse arguments
program.parse(process.argv);

// Show help if no command
if (!process.argv.slice(2).length) {
  program.outputHelp();
}