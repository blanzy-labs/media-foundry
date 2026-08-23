extends Node2D

const W := 540.0
const H := 960.0
const TOTAL_FRAMES := 450
const FPS := 30.0

var fixture: Dictionary
var frame_index := -1
var font: Font
var fixture_path := ""
var output_dir := ""

func _ready() -> void:
	fixture_path = _argument_value("--fixture")
	output_dir = _argument_value("--output-dir")
	if fixture_path.is_empty() or output_dir.is_empty():
		_fail("MF_RENDER_ERROR missing --fixture or --output-dir")
		return
	var file := FileAccess.open(fixture_path, FileAccess.READ)
	if file == null:
		_fail("MF_RENDER_ERROR fixture unreadable: " + fixture_path)
		return
	var parsed = JSON.parse_string(file.get_as_text())
	if typeof(parsed) != TYPE_DICTIONARY:
		_fail("MF_RENDER_ERROR fixture is not valid JSON")
		return
	fixture = parsed
	if not _valid_fixture():
		_fail("MF_RENDER_ERROR fixture contract invalid")
		return
	DirAccess.make_dir_recursive_absolute(output_dir)
	font = ThemeDB.fallback_font
	print("MF_RENDER_START id=%s frames=%d fps=%d" % [fixture.id, TOTAL_FRAMES, int(FPS)])
	RenderingServer.set_default_clear_color(Color("18110e"))

func _process(_delta: float) -> void:
	if fixture.is_empty():
		return
	frame_index += 1
	if frame_index >= TOTAL_FRAMES:
		print("MF_RENDER_COMPLETE frames=%d" % TOTAL_FRAMES)
		get_tree().quit(0)
		return
	queue_redraw()
	await RenderingServer.frame_post_draw
	_capture_frame()

func _capture_frame() -> void:
	var image := get_viewport().get_texture().get_image()
	var path := output_dir.path_join("frame_%06d.png" % frame_index)
	var error := image.save_png(path)
	if error != OK:
		_fail("MF_RENDER_ERROR could not save " + path)
	if frame_index % 30 == 0:
		print("MF_RENDER_FRAME %d" % frame_index)

func _draw() -> void:
	if fixture.is_empty():
		return
	var t := float(frame_index) / FPS
	# Warm ink and paper base with deterministic physical-looking marks.
	draw_rect(Rect2(0, 0, W, H), Color("1b1410"))
	for i in range(28):
		var x := float((i * 83 + 17) % 540)
		var y := float((i * 137 + 41) % 960)
		var radius := float(10 + (i * 11) % 44)
		draw_circle(Vector2(x, y), radius, Color(0.55, 0.35, 0.18, 0.045))
	_draw_edge_stitches()
	if t < 2.0:
		_draw_intro(t)
	elif t < 5.0:
		_draw_reveal(t)
	elif t < 12.0:
		_draw_main(t)
	else:
		_draw_outro(t)

func _draw_intro(t: float) -> void:
	var entrance := _ease_out_back(clamp(t / 0.8, 0.0, 1.0))
	var angle: float = lerp(-0.12, -0.025, entrance)
	var panel := Rect2(42, lerp(-220.0, 326.0, entrance), 456, 272)
	draw_set_transform(panel.get_center(), angle)
	draw_rect(Rect2(-panel.size / 2.0, panel.size), Color("e7bd69"), true)
	draw_rect(Rect2(-panel.size / 2.0, panel.size), Color("4a2a1b"), false, 8)
	_center_text(str(fixture.intro.text), Vector2(0, -34), 42, Color("21150f"), 390)
	_center_text("A TINY FACTORY TEST", Vector2(0, 62), 19, Color("754026"), 390)
	draw_set_transform(Vector2.ZERO, 0.0)

func _draw_reveal(t: float) -> void:
	var p := _smoothstep(clamp((t - 2.0) / 1.0, 0.0, 1.0))
	var center := Vector2(W / 2.0, lerp(1080.0, 485.0, p))
	draw_set_transform(center, lerp(0.08, -0.025, p))
	draw_rect(Rect2(-225, -265, 450, 530), Color("c56b3d"), true)
	draw_rect(Rect2(-225, -265, 450, 530), Color("542719"), false, 9)
	for y in range(-225, 240, 58):
		draw_line(Vector2(-190, y), Vector2(190, y + 8), Color(0.25, 0.10, 0.06, 0.15), 3)
	_center_text("CONTENT", Vector2(0, -64), 50, Color("fff0c5"), 390)
	_center_text("MEETS", Vector2(0, 12), 30, Color("482219"), 390)
	_center_text("CODE", Vector2(0, 90), 62, Color("fff0c5"), 390)
	draw_set_transform(Vector2.ZERO, 0.0)
	var dot_x: float = lerp(-50.0, W + 50.0, clamp((t - 2.2) / 2.7, 0.0, 1.0))
	draw_circle(Vector2(dot_x, 180 + sin(t * 8.0) * 35.0), 24, Color("85c7a5"))

func _draw_main(t: float) -> void:
	var settle := _ease_out_back(clamp((t - 5.0) / 0.9, 0.0, 1.0))
	var bob := sin((t - 5.0) * 2.4) * 5.0
	var card_center := Vector2(W / 2.0, lerp(1040.0, 480.0, settle) + bob)
	draw_set_transform(card_center, -0.018)
	draw_rect(Rect2(-230, -320, 460, 640), Color("eadba9"), true)
	draw_rect(Rect2(-230, -320, 460, 640), Color("462a1d"), false, 9)
	draw_rect(Rect2(-202, -286, 404, 14), Color("b64e32"), true)
	_center_text(str(fixture.content.headline), Vector2(0, -155), 43, Color("2d211a"), 400)
	_center_text(str(fixture.content.body), Vector2(0, 32), 29, Color("49362a"), 380)
	_center_text("DATA  →  FRAMES  →  PROOF", Vector2(0, 218), 18, Color("9b492f"), 390)
	draw_set_transform(Vector2.ZERO, 0.0)
	# A deliberately chunky animated gear proves non-text animation.
	var gear := Vector2(442, 752)
	draw_set_transform(gear, t * 1.7)
	for i in range(8):
		var a := TAU * float(i) / 8.0
		draw_rect(Rect2(Vector2(cos(a), sin(a)) * 45.0 - Vector2(9, 16), Vector2(18, 32)), Color("e4a64c"), true)
	draw_circle(Vector2.ZERO, 42, Color("e4a64c"))
	draw_circle(Vector2.ZERO, 17, Color("1b1410"))
	draw_set_transform(Vector2.ZERO, 0.0)

func _draw_outro(t: float) -> void:
	var p := _ease_out_back(clamp((t - 12.0) / 0.8, 0.0, 1.0))
	var scale_value: float = lerp(0.25, 1.0, p)
	draw_set_transform(Vector2(W / 2.0, H / 2.0), sin(t * 1.8) * 0.012, Vector2.ONE * scale_value)
	draw_circle(Vector2.ZERO, 232, Color("6d9d78"))
	draw_circle(Vector2.ZERO, 218, Color("223528"))
	_center_text(str(fixture.outro.text), Vector2(0, -24), 49, Color("f1d590"), 410)
	_center_text("MADE BY MACHINES. JUDGED BY TESTS.", Vector2(0, 70), 17, Color("bad6b9"), 410)
	draw_set_transform(Vector2.ZERO, 0.0)

func _draw_edge_stitches() -> void:
	for y in range(24, 960, 34):
		draw_line(Vector2(15, y), Vector2(25, y + 8), Color("9e6b42"), 2)
		draw_line(Vector2(515, y + 8), Vector2(525, y), Color("9e6b42"), 2)

func _center_text(value: String, center: Vector2, size: int, color: Color, max_width: float) -> void:
	var words := value.split(" ")
	var lines: Array[String] = []
	var line := ""
	for word in words:
		var candidate := word if line.is_empty() else line + " " + word
		if font.get_string_size(candidate, HORIZONTAL_ALIGNMENT_LEFT, -1, size).x > max_width and not line.is_empty():
			lines.append(line)
			line = word
		else:
			line = candidate
	if not line.is_empty():
		lines.append(line)
	var line_height := float(size) * 1.18
	var start_y := center.y - (float(lines.size() - 1) * line_height / 2.0)
	for i in range(lines.size()):
		var width := font.get_string_size(lines[i], HORIZONTAL_ALIGNMENT_LEFT, -1, size).x
		draw_string(font, Vector2(center.x - width / 2.0, start_y + i * line_height), lines[i], HORIZONTAL_ALIGNMENT_LEFT, -1, size, color)

func _valid_fixture() -> bool:
	if not fixture.has_all(["id", "template", "format", "intro", "content", "outro", "audio"]):
		return false
	if fixture.template != "did_you_know":
		return false
	var format: Dictionary = fixture.format
	return format.get("width") == 1080 and format.get("height") == 1920 and format.get("fps") == 30 and format.get("duration_seconds") == 15

func _argument_value(key: String) -> String:
	var args := OS.get_cmdline_user_args()
	for i in range(args.size() - 1):
		if args[i] == key:
			return ProjectSettings.globalize_path(args[i + 1])
	return ""

func _smoothstep(value: float) -> float:
	return value * value * (3.0 - 2.0 * value)

func _ease_out_back(value: float) -> float:
	var c1 := 1.70158
	var c3 := c1 + 1.0
	return 1.0 + c3 * pow(value - 1.0, 3.0) + c1 * pow(value - 1.0, 2.0)

func _fail(message: String) -> void:
	printerr(message)
	get_tree().quit(1)
