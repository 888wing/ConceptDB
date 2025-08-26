/**
 * Jest test setup
 */

// Add any global test setup here
beforeAll(() => {
  // Set test environment variables
  process.env.NODE_ENV = 'test';
});

// Clean up after all tests
afterAll(() => {
  // Clean up
});

// Extend Jest matchers if needed
expect.extend({
  toBeConceptDBError(received: any) {
    const pass = received && received.name && received.name.includes('ConceptDBError');
    return {
      pass,
      message: () => pass
        ? `Expected ${received} not to be a ConceptDBError`
        : `Expected ${received} to be a ConceptDBError`
    };
  }
});