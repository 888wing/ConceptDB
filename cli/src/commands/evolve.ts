import chalk from 'chalk';
import axios from 'axios';
import ora from 'ora';
import * as fs from 'fs';
import * as path from 'path';

interface EvolveOptions {
  metrics?: boolean;
  simulate?: boolean;
}

export async function evolveCommand(phase?: string, options: EvolveOptions = {}) {
  const spinner = ora();
  
  // Load configuration
  const configPath = path.join(process.cwd(), '.conceptdb');
  let apiUrl = 'http://localhost:8000';
  let currentPhase = 1;
  
  if (fs.existsSync(configPath)) {
    const config = JSON.parse(fs.readFileSync(configPath, 'utf-8'));
    apiUrl = config.api?.url || apiUrl;
    currentPhase = config.evolution?.currentPhase || 1;
  }
  
  try {
    if (options.metrics || !phase) {
      // Show evolution metrics
      spinner.start('Fetching evolution metrics...');
      
      const response = await axios.get(`${apiUrl}/api/v1/metrics/evolution`);
      const metrics = response.data;
      
      spinner.succeed('Evolution metrics loaded');
      
      console.log('\n' + chalk.bold('📊 Evolution Metrics'));
      console.log(chalk.gray('═'.repeat(50)));
      
      // Current phase visualization
      const phases = [1, 2, 3, 4];
      const phaseBar = phases.map(p => {
        if (p < metrics.phase) return chalk.green('●');
        if (p === metrics.phase) return chalk.yellow('◉');
        return chalk.gray('○');
      }).join('──');
      
      console.log(`Phase Progress: ${phaseBar}`);
      console.log(`Current Phase: ${chalk.yellow(`Phase ${metrics.phase}`)}`);
      console.log(`Conceptualization: ${chalk.cyan((metrics.conceptualization_ratio * 100).toFixed(1) + '%')}`);
      console.log();
      
      // Query statistics
      console.log(chalk.bold('Query Distribution:'));
      const total = metrics.total_queries || 1;
      const postgresPercent = ((metrics.postgres_queries / total) * 100).toFixed(1);
      const conceptPercent = ((metrics.concept_queries / total) * 100).toFixed(1);
      const hybridPercent = ((metrics.hybrid_queries / total) * 100).toFixed(1);
      
      console.log(`  PostgreSQL: ${createBar(parseFloat(postgresPercent))} ${postgresPercent}%`);
      console.log(`  Concepts:   ${createBar(parseFloat(conceptPercent))} ${conceptPercent}%`);
      console.log(`  Hybrid:     ${createBar(parseFloat(hybridPercent))} ${hybridPercent}%`);
      console.log();
      
      // Confidence score
      if (metrics.avg_concept_confidence) {
        const confidence = (metrics.avg_concept_confidence * 100).toFixed(1);
        const confColor = metrics.avg_concept_confidence > 0.7 ? chalk.green :
                         metrics.avg_concept_confidence > 0.5 ? chalk.yellow : chalk.red;
        console.log(`Concept Confidence: ${confColor(confidence + '%')}`);
      }
      
      console.log();
      console.log(chalk.bold('Recommendation:'));
      console.log(chalk.gray(metrics.recommendation));
      console.log(chalk.gray('═'.repeat(50)));
      
      // Evolution path
      console.log('\n' + chalk.bold('Evolution Path:'));
      displayEvolutionPath(metrics.phase);
      
    } else {
      // Trigger evolution to specific phase
      const targetPhase = parseInt(phase);
      
      if (isNaN(targetPhase) || targetPhase < 2 || targetPhase > 4) {
        console.error(chalk.red('Error: Phase must be 2, 3, or 4'));
        process.exit(1);
      }
      
      if (targetPhase <= currentPhase) {
        console.error(chalk.red(`Error: Already at phase ${currentPhase} or higher`));
        process.exit(1);
      }
      
      console.log(chalk.cyan(`\n🚀 Evolution to Phase ${targetPhase}\n`));
      
      if (options.simulate) {
        console.log(chalk.yellow('SIMULATION MODE - No changes will be applied\n'));
      }
      
      // Show what will happen
      const phaseInfo = getPhaseInfo(targetPhase);
      console.log(chalk.bold('Target Configuration:'));
      console.log(chalk.gray('─'.repeat(40)));
      console.log(`Phase: ${chalk.yellow(targetPhase)}`);
      console.log(`Conceptualization: ${chalk.cyan(phaseInfo.ratio)}`);
      console.log(`Architecture: ${chalk.gray(phaseInfo.architecture)}`);
      console.log(chalk.gray('─'.repeat(40)));
      
      console.log('\n' + chalk.bold('Migration Steps:'));
      phaseInfo.steps.forEach((step: string, i: number) => {
        console.log(`  ${i + 1}. ${step}`);
      });
      
      if (!options.simulate) {
        // Actually trigger evolution
        spinner.start('Initiating evolution...');
        
        const response = await axios.post(`${apiUrl}/api/v1/evolve`, {
          target_phase: targetPhase
        });
        
        spinner.succeed('Evolution initiated');
        
        console.log('\n' + chalk.green('✓ Evolution process started'));
        console.log(chalk.gray(response.data.status));
        
        // Update local config
        if (fs.existsSync(configPath)) {
          const config = JSON.parse(fs.readFileSync(configPath, 'utf-8'));
          config.evolution.currentPhase = targetPhase;
          config.evolution.conceptualizationRatio = parseFloat(phaseInfo.ratio) / 100;
          fs.writeFileSync(configPath, JSON.stringify(config, null, 2));
        }
      } else {
        console.log('\n' + chalk.yellow('Simulation complete - no changes applied'));
      }
    }
    
  } catch (error: any) {
    spinner.fail('Operation failed');
    if (error.response) {
      console.error(chalk.red(`Error: ${error.response.data.detail || error.response.data.error}`));
    } else {
      console.error(chalk.red(`Error: ${error.message}`));
      console.log(chalk.yellow('Make sure the API is running (conceptdb dev)'));
    }
    process.exit(1);
  }
}

function createBar(percent: number): string {
  const width = 20;
  const filled = Math.round((percent / 100) * width);
  const bar = '█'.repeat(filled) + '░'.repeat(width - filled);
  
  if (percent > 70) return chalk.green(bar);
  if (percent > 30) return chalk.yellow(bar);
  return chalk.red(bar);
}

function displayEvolutionPath(currentPhase: number) {
  const phases = [
    { phase: 1, ratio: '10%', name: 'Enhancement Layer' },
    { phase: 2, ratio: '30%', name: 'Hybrid Storage' },
    { phase: 3, ratio: '70%', name: 'Concept-First' },
    { phase: 4, ratio: '100%', name: 'Pure Concepts' }
  ];
  
  phases.forEach(p => {
    const marker = p.phase < currentPhase ? chalk.green('✓') :
                  p.phase === currentPhase ? chalk.yellow('●') :
                  chalk.gray('○');
    const color = p.phase <= currentPhase ? chalk.white : chalk.gray;
    
    console.log(`  ${marker} Phase ${p.phase}: ${color(p.ratio)} - ${color(p.name)}`);
  });
}

function getPhaseInfo(phase: number) {
  const phases: { [key: number]: any } = {
    2: {
      ratio: '30%',
      architecture: 'Hybrid storage with intelligent routing',
      steps: [
        'Increase concept extraction rate',
        'Enhance query router intelligence',
        'Implement write-through caching',
        'Add concept-based indexing'
      ]
    },
    3: {
      ratio: '70%',
      architecture: 'Concept-first with PostgreSQL backup',
      steps: [
        'Make concepts primary storage',
        'PostgreSQL becomes fallback',
        'Implement concept-based transactions',
        'Full natural language interface'
      ]
    },
    4: {
      ratio: '100%',
      architecture: 'Pure concept database',
      steps: [
        'Complete conceptualization',
        'Remove PostgreSQL dependency',
        'Pure concept operations',
        'Advanced AI integration'
      ]
    }
  };
  
  return phases[phase];
}