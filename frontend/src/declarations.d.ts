// Allow importing CSS modules in TypeScript
// Place this file in your src/ directory

declare module '*.module.css' {
  const classes: { [key: string]: string };
  export default classes;
}
