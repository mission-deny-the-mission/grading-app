{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  name = "test-shell";
  buildInputs = []; 
  shellHook = "\n    echo \"This is a test shell hook\"\n    exit 1\n  ";
}
