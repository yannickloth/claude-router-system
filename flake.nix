{
  description = "Claude Code router system and general-purpose agents";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    with flake-utils.lib; eachSystem allSystems (system:
    let
      pkgs = nixpkgs.legacyPackages.${system};
    in {
      devShells.default = pkgs.mkShell {
        buildInputs = [
          pkgs.gh
          pkgs.shellcheck
          (pkgs.python312.withPackages (ps: with ps; [
            networkx
            pyyaml
            pytest
          ]))
          pkgs.bun
          pkgs.nodejs
        ];
      };
    });
}
