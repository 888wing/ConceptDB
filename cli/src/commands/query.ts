import { Command } from 'commander';
import chalk from 'chalk';
import ora from 'ora';
import { ConceptDBClient } from '../utils/client';

export const queryCommand = new Command('query')
  .description('Execute a query on ConceptDB')
  .argument('<query>', 'Query to execute (SQL or natural language)')
  .option('-e, --explain', 'Explain query routing')
  .action(async (query: string, options: any) => {
    const spinner = ora('Executing query...').start();
    
    try {
      const client = new ConceptDBClient();
      
      if (options.explain) {
        spinner.text = 'Analyzing query...';
        const explanation = await client.explainQuery(query);
        spinner.succeed('Query analyzed');
        
        console.log('\n' + chalk.bold('Query Analysis:'));
        console.log(chalk.cyan('Type:'), explanation.analysis.type);
        console.log(chalk.cyan('Routing:'), explanation.analysis.routing);
        console.log(chalk.cyan('Confidence:'), explanation.analysis.confidence);
      } else {
        const result = await client.query(query);
        spinner.succeed('Query executed');
        console.log(result);
      }
    } catch (error: any) {
      spinner.fail('Query failed');
      console.error(chalk.red('Error:'), error.message);
      process.exit(1);
    }
  });
