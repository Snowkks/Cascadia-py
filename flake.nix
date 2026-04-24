{
  description = "Cascadia – Digital Board Game (Python/Pygame)";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        python = pkgs.python311;

        cascadia = python.pkgs.buildPythonApplication {
          pname = "cascadia";
          version = "1.0.0";
          src = ./.;

          format = "other";

          propagatedBuildInputs = with python.pkgs; [
            pygame
          ];

          # No build step – pure source app
          buildPhase = "true";

          installPhase = ''
            mkdir -p $out/lib/cascadia $out/bin

            # Copy source tree
            cp -r cascadia $out/lib/cascadia/cascadia
            cp    main.py  $out/lib/cascadia/main.py

            # Create writable data/saves dirs at runtime in $HOME
            cat > $out/bin/cascadia <<EOF
            #!/usr/bin/env bash
            mkdir -p "\$HOME/.local/share/cascadia/data"
            mkdir -p "\$HOME/.local/share/cascadia/saves"
            cd $out/lib/cascadia
            exec ${python.interpreter} main.py "\$@"
            EOF
            chmod +x $out/bin/cascadia
          '';

          # Patch constants.py so DB/saves go to $HOME at runtime
          postPatch = ''
            substituteInPlace cascadia/constants.py \
              --replace \
                'DB_PATH    = os.path.join(DATA_DIR, "cascadia.db")' \
                'DB_PATH    = os.path.join(os.path.expanduser("~/.local/share/cascadia/data"), "cascadia.db")'
          '';

          meta = {
            description = "Cascadia board game digital edition";
            mainProgram  = "cascadia";
          };
        };

        # Dev shell with pygame + pytest available
        devShell = pkgs.mkShell {
          name = "cascadia-dev";

          buildInputs = [
            python
            python.pkgs.pygame
            python.pkgs.pytest

            # Needed by pygame on NixOS (SDL2 stack)
            pkgs.SDL2
            pkgs.SDL2_mixer
            pkgs.SDL2_image
            pkgs.SDL2_ttf
            pkgs.libGL
            pkgs.xorg.libX11
          ];

          shellHook = ''
            echo "🌲 Cascadia dev shell ready"
            echo "  Run game : python main.py"
            echo "  Run tests: pytest tests/ -v"
            export SDL_VIDEODRIVER=''${SDL_VIDEODRIVER:-x11}
            # Keep DB/saves local to project during development
            export CASCADIA_DEV=1
          '';
        };

      in {
        packages.default  = cascadia;
        packages.cascadia = cascadia;

        devShells.default = devShell;

        apps.default = flake-utils.lib.mkApp {
          drv  = cascadia;
          name = "cascadia";
        };
      }
    );
}
