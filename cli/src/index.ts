#!/usr/bin/env node

import { Command } from 'commander';
import chalk from 'chalk';
import ora from 'ora';
import dotenv from 'dotenv';
import { queryCommand } from './commands/query';
import { initCommand } from './commands/init';
import { devCommand } from './commands/dev';
import { statusCommand } from './commands/status';
import { importCommand } from './commands/import';

// Load environment variables
dotenv.config();

const program = new Command();

// ASCII Art Logo
const logo = `
╔═══════════════════════════════════════╗
║     ____                           _   ║
║    / ___|___  _ __   ___ ___ _ __ | |_ ║
║   | |   / _ \\| '_ \\ / __/ _ \\ '_ \\| __|║
║   | |__| (_) | | | | (_|  __/ |_) | |_ ║
║    \\____\\___/|_| |_|\\___\\___| .__/ \\__|║
║                              |_|  DB    ║
╚═══════════════════════════════════════╝
`;

// Main CLI setup
program
  .name('conceptdb')
  .description('ConceptDB CLI - Evolutionary Concept-Type Database')
  .version('0.1.0')
  .addHelpText('before', chalk.cyan(logo));

// Add commands
program.addCommand(queryCommand);
program.addCommand(initCommand);
program.addCommand(devCommand);
program.addCommand(statusCommand);
program.addCommand(importCommand);

// Global options
program
  .option('-h, --host <host>', 'ConceptDB server host', process.env.CONCEPTDB_HOST || 'localhost')
  .option('-p, --port <port>', 'ConceptDB server port', process.env.CONCEPTDB_PORT || '8000')
  .option('--json', 'Output in JSON format')
  .option('--verbose', 'Verbose output');

// Parse arguments
program.parse(process.argv);

// Show help if no command provided
if (!process.argv.slice(2).length) {
  program.outputHelp();
}
