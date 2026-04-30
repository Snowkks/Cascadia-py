{
  description = "Cascadia – Digital Board Game (Python/Pygame)";

  inputs = {
    nixpkgs.url     = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs   = nixpkgs.legacyPackages.${system};
        python = pkgs.python311;

        cascadia = python.pkgs.buildPythonApplication {
          pname   = "cascadia";
          version = "1.0.0";
          src     = ./.;
          format  = "other";

          propagatedBuildInputs = with python.pkgs; [ pygame ];

          buildPhase = "true";

          installPhase = ''
            mkdir -p $out/lib/cascadia $out/bin

            cp -r cascadia $out/lib/cascadia/cascadia
            cp    main.py  $out/lib/cascadia/main.py

            # Patch DB path to write to $HOME at runtime
            substituteInPlace $out/lib/cascadia/cascadia/constants.py \
              --replace \
                'DB_PATH    = os.path.join(DATA_DIR, "cascadia.db")' \
                'DB_PATH    = os.path.join(os.path.expanduser("~/.local/share/cascadia/data"), "cascadia.db")'

            cat > $out/bin/cascadia <<'EOF'
#!/usr/bin/env bash
# Create runtime dirs
mkdir -p "$HOME/.local/share/cascadia/data"
mkdir -p "$HOME/.local/share/cascadia/saves"

# On Wayland (Hyprland etc.) use XWayland for correct mouse coords.
# Pass --wayland to override.
if [ -n "$WAYLAND_DISPLAY" ] && [ "$1" != "--wayland" ]; then
  export SDL_VIDEODRIVER=x11
  export DISPLAY="''${DISPLAY:-:0}"
fi

cd ${placeholder "out"}/lib/cascadia
exec ${python.interpreter} main.py "$@"
EOF
            chmod +x $out/bin/cascadia
          '';

          meta.description = "Cascadia board game – digital edition";
          meta.mainProgram  = "cascadia";
        };

        devShell = pkgs.mkShell {
          name = "cascadia-dev";
          buildInputs = [
            python
            python.pkgs.pygame
            python.pkgs.pytest
            pkgs.SDL2
            pkgs.SDL2_mixer
            pkgs.SDL2_image
            pkgs.SDL2_ttf
            pkgs.libGL
            pkgs.xorg.libX11
            pkgs.xorg.libXi
            pkgs.xorg.libXcursor
          ];

          shellHook = ''
            echo "🌲 Cascadia dev shell"
            echo "  python main.py           – run game (auto XWayland on Wayland)"
            echo "  python main.py --wayland – native Wayland SDL"
            echo "  pytest tests/ -v         – run unit tests"

            # Auto-switch to XWayland if under Wayland
            if [ -n "$WAYLAND_DISPLAY" ] && [ -z "$CASCADIA_WAYLAND" ]; then
              export SDL_VIDEODRIVER=x11
              export DISPLAY="''${DISPLAY:-:0}"
              echo "  [XWayland mode active — SDL_VIDEODRIVER=x11]"
            fi
          '';
        };

      in {
        packages.default  = cascadia;
        packages.cascadia = cascadia;
        devShells.default = devShell;
        apps.default = flake-utils.lib.mkApp { drv = cascadia; name = "cascadia"; };
      }
    );
}
