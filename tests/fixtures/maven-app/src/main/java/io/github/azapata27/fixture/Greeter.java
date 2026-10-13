package io.github.azapata27.fixture;

/** Trivial production code so the fixture has something to compile and test. */
public final class Greeter {

    private Greeter() {
    }

    public static String greet(String name) {
        if (name == null || name.isBlank()) {
            return "Hello, world!";
        }
        return "Hello, " + name.strip() + "!";
    }
}
