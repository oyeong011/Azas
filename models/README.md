# Azas Tumbler And Dispenser Models

Generated from LLM Wiki page `[[User Supplied Tumbler And Dispenser Specs]]`.

## Files

- `azas_tumbler_shaker.obj`: ShakeBaby-style tumbler/shaker approximation.
- `azas_dispenser_single.obj`: single transparent bottle and black pump head.
- `azas_four_dispenser_row.obj`: four fixed dispensers in a row, 85 mm spacing.
- `azas_tumbler_dispenser_preview.obj`: four-dispenser row plus tumbler preview.
- `azas_tumbler_dispenser_preview.usda`: Isaac Sim friendly stage referencing the OBJ assets.
- `azas_models.mtl`: shared OBJ material file.

## Source Dimensions

Tumbler: 75 mm diameter, 170 mm lidded height, 140 mm lidless body height.

Dispenser: 58 mm bottle width reference, 275 mm bottle height, 18/28 mm mouth inner/outer diameter, 205 mm tube length, 7/8.5 mm tube inner/outer diameter, 195 mm pump head length, 117 mm exposed pump portion.

## Usage

RViz can load the OBJ meshes through a `visualization_msgs/Marker` with `type=MESH_RESOURCE` once the assets are installed into a ROS package. In this workspace they are also copied into the `jarvis` package under `/home/ssu/ros2_ws/src/Azas/models`.

Isaac Sim can import the OBJ files directly or open `azas_tumbler_dispenser_preview.usda` as a lightweight stage.

These models are visualization/digital-twin approximations. Do not use them as calibrated collision geometry for real robot execution until measured against the physical cell.
