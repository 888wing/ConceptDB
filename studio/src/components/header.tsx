'use client';

import { useState, useEffect } from 'react';
import { Brain, Database, Loader2, Moon, Sun } from 'lucide-react';
import { useTheme } from 'next-themes';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useConceptDB } from '@/lib/conceptdb-context';
import { cn } from '@/lib/utils';

export function Header() {
  const { theme, setTheme } = useTheme();
  const { isConnected, metrics } = useConceptDB();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-14 items-center">
        <div className="mr-4 flex">
          <a className="mr-6 flex items-center space-x-2" href="/">
            <Brain className="h-6 w-6 text-primary" />
            <span className="hidden font-bold sm:inline-block">
              ConceptDB Studio
            </span>
          </a>
          <nav className="flex items-center space-x-6 text-sm font-medium">
            <div className="flex items-center space-x-2">
              <div
                className={cn(
                  'h-2 w-2 rounded-full',
                  isConnected ? 'bg-green-500' : 'bg-red-500'
                )}
              />
              <span className="text-muted-foreground">
                {isConnected ? 'Connected' : 'Disconnected'}
              </span>
            </div>
            {metrics && (
              <div className="flex items-center space-x-4 text-sm">
                <div className="flex items-center space-x-1">
                  <Database className="h-4 w-4 text-postgres" />
                  <span>{metrics.sql_queries || 0}</span>
                </div>
                <div className="flex items-center space-x-1">
                  <Brain className="h-4 w-4 text-concept" />
                  <span>{metrics.concept_queries || 0}</span>
                </div>
                <div className="text-muted-foreground">
                  Phase {metrics.current_phase} • {metrics.conceptualization_ratio}% Concepts
                </div>
              </div>
            )}
          </nav>
        </div>
        <div className="flex flex-1 items-center justify-between space-x-2 md:justify-end">
          {mounted && (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon">
                  {theme === 'light' ? (
                    <Sun className="h-5 w-5" />
                  ) : theme === 'dark' ? (
                    <Moon className="h-5 w-5" />
                  ) : (
                    <Loader2 className="h-5 w-5 animate-spin" />
                  )}
                  <span className="sr-only">Toggle theme</span>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={() => setTheme('light')}>
                  Light
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => setTheme('dark')}>
                  Dark
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => setTheme('system')}>
                  System
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          )}
        </div>
      </div>
    </header>
  );
}