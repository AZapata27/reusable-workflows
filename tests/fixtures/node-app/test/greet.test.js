import { test } from 'node:test';
import assert from 'node:assert/strict';
import { greet } from '../src/greet.js';

test('greets by name', () => {
  assert.equal(greet('  Ada '), 'Hello, Ada!');
});

test('falls back when name is blank', () => {
  assert.equal(greet(' '), 'Hello, world!');
  assert.equal(greet(undefined), 'Hello, world!');
});
