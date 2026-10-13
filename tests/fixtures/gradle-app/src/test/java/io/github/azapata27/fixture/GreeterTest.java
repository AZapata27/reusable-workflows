package io.github.azapata27.fixture;

import static org.junit.jupiter.api.Assertions.assertEquals;

import org.junit.jupiter.api.Test;

class GreeterTest {

    @Test
    void greetsByName() {
        assertEquals("Hello, Ada!", Greeter.greet("  Ada "));
    }

    @Test
    void fallsBackWhenNameIsBlank() {
        assertEquals("Hello, world!", Greeter.greet(" "));
        assertEquals("Hello, world!", Greeter.greet(null));
    }
}
