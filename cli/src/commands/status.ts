import { Command } from 'commander';
import chalk from 'chalk';
import ora from 'ora';
import { ConceptDBClient } from '../utils/client';
import { table } from 'table';

export const statusCommand = new Command('status')
  .description('Check ConceptDB status and evolution metrics')
  .option('-v, --verbose', 'Show detailed status information')
  .action(async (options: any) => {
    const spinner = ora('Checking ConceptDB status...').start();
    
    try {
      const client = new ConceptDBClient();
      
      // Check health
      const health = await client.getHealth();
      
      if (health.status === 'healthy') {
        spinner.succeed('ConceptDB is healthy');
      } else if (health.status === 'degraded') {
        spinner.warn('ConceptDB is degraded');
      } else {
        spinner.fail('ConceptDB is unhealthy');
      }
      
      // Get evolution metrics
      spinner.start('Fetching evolution metrics...');
      const metrics = await client.getEvolutionMetrics();
      spinner.stop();
      
      // Display overview
      console.log('\n' + chalk.bold('📊 System Overview'));
      console.log(chalk.gray('─'.repeat(50)));
      
      const overviewData = [
        ['Component', 'Status', 'Details'],
        ['API Server', health.status === 'healthy' ? '✅ Running' : '❌ Down', `Port ${process.env.CONCEPTDB_PORT || 8000}`],
        ['PostgreSQL', health.postgres ? '✅ Connected' : '❌ Disconnected', health.postgres_details || 'N/A'],
        ['Qdrant', health.qdrant ? '✅ Connected' : '❌ Disconnected', health.qdrant_details || 'N/A'],
        ['SQLite', health.sqlite ? '✅ Ready' : '❌ Not Ready', health.sqlite_details || 'N/A']
      ];
      
      console.log(table(overviewData, {
        border: {
          topBody: '─',
          topJoin: '┬',
          topLeft: '┌',
          topRight: '┐',
          bottomBody: '─',
          bottomJoin: '┴',
          bottomLeft: '└',
          bottomRight: '┘',
          bodyLeft: '│',
          bodyRight: '│',
          bodyJoin: '│',
          joinBody: '─',
          joinLeft: '├',
          joinRight: '┤',
          joinJoin: '┼'
        }
      }));
      
      // Display evolution metrics
      console.log(chalk.bold('🧬 Evolution Metrics'));
      console.log(chalk.gray('─'.repeat(50)));
      
      const phase = metrics.current_phase;
      const conceptRatio = metrics.conceptualization_ratio;
      const totalQueries = metrics.total_queries || 0;
      const conceptQueries = metrics.concept_queries || 0;
      const sqlQueries = metrics.sql_queries || 0;
      
      console.log(`Current Phase: ${chalk.yellow(`Phase ${phase} (${conceptRatio * 100}% conceptualization)`)}`);
      console.log(`Total Queries: ${chalk.cyan(totalQueries)}`);
      console.log(`  • Concept Layer: ${chalk.green(conceptQueries)} (${((conceptQueries/totalQueries) * 100 || 0).toFixed(1)}%)`);
      console.log(`  • SQL Layer: ${chalk.blue(sqlQueries)} (${((sqlQueries/totalQueries) * 100 || 0).toFixed(1)}%)`);
      
      // Progress bar for evolution
      const progressLength = 40;
      const filledLength = Math.round(conceptRatio * progressLength);
      const progressBar = '█'.repeat(filledLength) + '░'.repeat(progressLength - filledLength);
      
      console.log('\n' + chalk.bold('Evolution Progress:'));
      console.log(`[${progressBar}] ${(conceptRatio * 100).toFixed(0)}%`);
      console.log(chalk.gray(`Phase 1 → Phase 2 → Phase 3 → Phase 4`));
      
      // Show routing statistics if verbose
      if (options.verbose) {
        console.log('\n' + chalk.bold('📈 Routing Statistics'));
        console.log(chalk.gray('─'.repeat(50)));
        
        const routingStats = await client.getRoutingStats();
        
        const routingData = [
          ['Query Type', 'Count', 'Avg Response Time', 'Success Rate'],
          ['Natural Language', routingStats.nl_count || 0, `${routingStats.nl_avg_time || 0}ms`, `${routingStats.nl_success_rate || 0}%`],
          ['SQL', routingStats.sql_count || 0, `${routingStats.sql_avg_time || 0}ms`, `${routingStats.sql_success_rate || 0}%`],
          ['Hybrid', routingStats.hybrid_count || 0, `${routingStats.hybrid_avg_time || 0}ms`, `${routingStats.hybrid_success_rate || 0}%`]
        ];
        
        console.log(table(routingData));
        
        // Show recent concepts
        console.log(chalk.bold('🔮 Recent Concepts'));
        console.log(chalk.gray('─'.repeat(50)));
        
        const recentConcepts = await client.getRecentConcepts();
        if (recentConcepts && recentConcepts.length > 0) {
          recentConcepts.slice(0, 5).forEach((concept: any) => {
            console.log(`  • ${chalk.cyan(concept.name)} - ${chalk.gray(concept.created_at)}`);
          });
        } else {
          console.log(chalk.gray('  No concepts created yet'));
        }
      }
      
    } catch (error: any) {
      spinner.fail('Failed to get status');
      console.error(chalk.red('Error:'), error.message);
      process.exit(1);
    }
  });