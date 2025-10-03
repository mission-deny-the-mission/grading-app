# DEPRECATED: This configuration is deprecated in favor of flake.nix
# Please use 'nix develop' instead of 'nix-shell'

{ pkgs ? import <nixpkgs> {} }:

let
  pkgs = import <nixpkgs> {};
  # Create a more obtrusive deprecation
  deprecatedEnv = pkgs.runCommand "deprecated-warning" { }
    ''
      echo "🚨 NIX-SHELL CONFIGURATION IS DEPRECATED 🚨" >&2
      echo "This nix-shell configuration has been deprecated in favor of flake.nix" >&2
      echo "" >&2
      echo "Please use 'nix develop' instead which uses the modern flake approach" >&2
      echo "Or enter the directory with direnv enabled (which uses 'use flake')" >&2
      echo "" >&2
      echo "To enter the new environment:" >&2
      echo "  nix develop" >&2
      echo "" >&2
      touch $out
    '';
in
pkgs.mkShell {
  name = "deprecated-nix-shell";

  buildInputs = with pkgs; [
    deprecatedEnv  # This will show the warning during build
  ];

  shellHook = ''
    # Show deprecation message every time a command is run
    echo "===========================================" >&2
    echo "🚨 NIX-SHELL IS DEPRECATED 🚨" >&2
    echo "===========================================" >&2
    echo "This nix-shell configuration has been deprecated." >&2
    echo "Please use 'nix develop' instead, which uses flake.nix" >&2
    echo "Or simply enter this directory with direnv enabled" >&2
    echo "" >&2
    echo "To enter the new environment:" >&2
    echo "  nix develop" >&2
    echo "===========================================" >&2

    # Function to show warning before each Python-related command
    show_warning() {
      echo "⚠️  WARNING: You are using deprecated nix-shell!" >&2
      echo "⚠️  Use 'nix develop' instead!" >&2
      echo "" >&2
    }

    # Override important functions to show warnings
    export -f show_warning
    alias python='show_warning; python'
    alias flask='show_warning; flask'
    alias celery='show_warning; celery'
    alias pytest='show_warning; pytest'
  '';
}
