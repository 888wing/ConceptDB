import { Command } from 'commander';
import chalk from 'chalk';
import ora from 'ora';
import { spawn } from 'child_process';
import axios from 'axios';
import fs from 'fs';
import path from 'path';

export const devCommand = new Command('dev')
  .description('Start ConceptDB development environment')
  .option('-p, --port <port>', 'API server port', '8000')
  .option('--no-postgres', 'Skip PostgreSQL startup')
  .option('-s, --studio', 'Also start Web Studio')
  .action(async (options: any) => {
    const spinner = ora('Starting ConceptDB development environment...').start();
    
    try {
      // Check if docker-compose exists
      const dockerComposePath = path.join(process.cwd(), 'docker-compose.yml');
      if (!fs.existsSync(dockerComposePath)) {
        spinner.fail('docker-compose.yml not found');
        console.log(chalk.yellow('\nRun "conceptdb init" first to create a project'));
        process.exit(1);
      }
      
      // Start services with docker-compose
      spinner.text = 'Starting Docker services...';
      
      const dockerProcess = spawn('docker-compose', ['up', '-d'], {
        cwd: process.cwd(),
        stdio: 'pipe'
      });
      
      await new Promise((resolve, reject) => {
        dockerProcess.on('close', (code) => {
          if (code === 0) {
            resolve(code);
          } else {
            reject(new Error(`Docker Compose exited with code ${code}`));
          }
        });
        
        dockerProcess.on('error', (error) => {
          reject(error);
        });
      });
      
      spinner.text = 'Waiting for services to be ready...';
      
      // Wait for services to be ready
      await waitForServices(options.port);
      
      spinner.succeed('Development environment is ready');
      
      // Display service URLs
      console.log('\n' + chalk.bold('📍 Service URLs:'));
      console.log(chalk.gray('─'.repeat(50)));
      console.log(`API:       ${chalk.green(`http://localhost:${options.port}`)}`);
      console.log(`API Docs:  ${chalk.green(`http://localhost:${options.port}/docs`)}`);
      console.log(`Qdrant:    ${chalk.green('http://localhost:6333/dashboard')}`);
      
      if (options.postgres !== false) {
        console.log(`PostgreSQL: ${chalk.green('postgresql://localhost:5433/conceptdb')}`);
      }
      
      if (options.studio) {
        console.log(`Web Studio: ${chalk.green('http://localhost:3000')}`);
      }
      
      console.log(chalk.gray('─'.repeat(50)));
      
      // Show helpful commands
      console.log('\n' + chalk.bold('📝 Quick Commands:'));
      console.log(chalk.gray('─'.repeat(50)));
      console.log(`${chalk.cyan('conceptdb query')} "find similar concepts"  ${chalk.gray('# Natural language')}`);
      console.log(`${chalk.cyan('conceptdb query')} "SELECT * FROM data"  ${chalk.gray('# SQL query')}`);
      console.log(`${chalk.cyan('conceptdb import')} data.csv  ${chalk.gray('# Import data')}`);
      console.log(`${chalk.cyan('conceptdb status')} --verbose  ${chalk.gray('# Check status')}`);
      console.log(chalk.gray('─'.repeat(50)));
      
      console.log('\n' + chalk.green('✨ Development environment is ready!'));
      console.log(chalk.gray('Press Ctrl+C to stop all services\n'));
      
      // Keep process running and handle shutdown
      process.on('SIGINT', async () => {
        console.log('\n' + chalk.yellow('Shutting down services...'));
        const stopProcess = spawn('docker-compose', ['down'], {
          cwd: process.cwd(),
          stdio: 'inherit'
        });
        stopProcess.on('close', () => {
          console.log(chalk.green('Services stopped successfully'));
          process.exit(0);
        });
      });
      
      // Keep the process running
      await new Promise(() => {});
      
    } catch (error: any) {
      spinner.fail('Failed to start development environment');
      console.error(chalk.red('Error:'), error.message);
      
      if (error.message.includes('docker')) {
        console.log(chalk.yellow('\nMake sure Docker is installed and running'));
      }
      
      process.exit(1);
    }
  });

async function waitForServices(port: string, maxRetries = 30): Promise<void> {
  for (let i = 0; i < maxRetries; i++) {
    try {
      // Check API health
      const response = await axios.get(`http://localhost:${port}/health`, {
        timeout: 1000
      });
      
      if (response.data.status === 'healthy' || response.data.status === 'degraded') {
        return;
      }
    } catch (error) {
      // Service not ready yet
    }
    
    // Wait 2 seconds before retrying
    await new Promise(resolve => setTimeout(resolve, 2000));
  }
  
  throw new Error('Services failed to start within timeout period');
}