/** Trivial production code so the fixture has something to test. */
export function greet(name) {
  const trimmed = typeof name === 'string' ? name.trim() : '';
  return trimmed ? `Hello, ${trimmed}!` : 'Hello, world!';
}
