import eslint from "@eslint/js";
import globals from "globals";
import tseslint from "typescript-eslint";

export default tseslint.config(
  { ignores: ["dist", "node_modules"] },
  eslint.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ["**/*.{ts,tsx}"],
    languageOptions: {
      ecmaVersion: 2022,
      globals: { ...globals.browser },
    },
    rules: {
      "@typescript-eslint/no-explicit-any": "off",
    },
  },
  {
    files: ["public/sw.js"],
    languageOptions: {
      globals: { ...globals.serviceworker },
    },
  },
);
