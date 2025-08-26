import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';
import chalk from 'chalk';

interface ConfigOptions {
  list?: boolean;
  global?: boolean;
}

export async function configCommand(key?: string, value?: string, options: ConfigOptions = {}) {
  // Determine config path
  const configPath = options.global 
    ? path.join(os.homedir(), '.conceptdb')
    : path.join(process.cwd(), '.conceptdb');
  
  // Load existing config or create new
  let config: any = {};
  if (fs.existsSync(configPath)) {
    config = JSON.parse(fs.readFileSync(configPath, 'utf-8'));
  }
  
  if (options.list || (!key && !value)) {
    // List all configuration
    console.log(chalk.bold('\n📋 ConceptDB Configuration\n'));
    console.log(chalk.gray('Location: ' + configPath));
    console.log(chalk.gray('─'.repeat(50)));
    displayConfig(config);
    return;
  }
  
  if (key && !value) {
    // Get specific value
    const val = getNestedValue(config, key);
    if (val !== undefined) {
      console.log(val);
    } else {
      console.log(chalk.yellow(`Configuration key '${key}' not found`));
      process.exit(1);
    }
    return;
  }
  
  if (key && value) {
    // Set value
    setNestedValue(config, key, value);
    fs.writeFileSync(configPath, JSON.stringify(config, null, 2));
    console.log(chalk.green(`✓ Set ${key} = ${value}`));
    return;
  }
}

function displayConfig(config: any, indent = 0) {
  const prefix = '  '.repeat(indent);
  
  for (const [key, value] of Object.entries(config)) {
    if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
      console.log(prefix + chalk.cyan(key) + ':');
      displayConfig(value, indent + 1);
    } else {
      const displayValue = Array.isArray(value) 
        ? `[${value.join(', ')}]`
        : String(value);
      console.log(prefix + chalk.cyan(key) + ': ' + chalk.white(displayValue));
    }
  }
}

function getNestedValue(obj: any, path: string): any {
  const keys = path.split('.');
  let current = obj;
  
  for (const key of keys) {
    if (current[key] === undefined) {
      return undefined;
    }
    current = current[key];
  }
  
  return current;
}

function setNestedValue(obj: any, path: string, value: string) {
  const keys = path.split('.');
  let current = obj;
  
  for (let i = 0; i < keys.length - 1; i++) {
    const key = keys[i];
    if (!(key in current) || typeof current[key] !== 'object') {
      current[key] = {};
    }
    current = current[key];
  }
  
  const lastKey = keys[keys.length - 1];
  
  // Try to parse value as JSON, number, or boolean
  let parsedValue: any = value;
  if (value === 'true') parsedValue = true;
  else if (value === 'false') parsedValue = false;
  else if (!isNaN(Number(value))) parsedValue = Number(value);
  else {
    try {
      parsedValue = JSON.parse(value);
    } catch {
      // Keep as string
    }
  }
  
  current[lastKey] = parsedValue;
}