import cadquery as cq
from click_cadquery import BuildParam, define_app
from click_cadquery.git import version_number as ver
from pydantic import Field


class Param(BuildParam):
    clock_width: float = Field(76.0, description="時計の幅 (mm)")
    clock_depth: float = Field(18.5, description="時計の厚み (mm)")
    holder_height: float = Field(50.0, description="内側の保持高さ (mm)")
    clearance: float = Field(0.4, description="時計と内壁の片側クリアランス (mm)")
    wall: float = Field(2.0, description="側壁・背面・底の厚み (mm)")
    frame_thickness: float = Field(2.0, description="前面フレームの厚み (mm)")
    frame_lip: float = Field(3.0, description="前面フレームが時計に被さる幅 (mm)")
    fillet: float = Field(1.0, description="外周の縦エッジのフィレット半径 (mm)")

    @property
    def filename(self) -> str:
        return (
            f"v{ver()}-{self.clock_width}w{self.holder_height}h"
            f"{self.clock_depth}d{self.frame_lip}l.stl"
        )


def build(param: Param) -> cq.Workplane:
    # 使用時と同じ向き (底が Z=0、上面開放) で作る。この向きのまま印刷できる。
    # 前面 (-Y) はコの字フレーム (左右 + 下)、時計は上から差し込む。
    inner_w = param.clock_width + 2 * param.clearance
    inner_d = param.clock_depth + 2 * param.clearance
    outer_w = inner_w + 2 * param.wall
    outer_d = param.frame_thickness + inner_d + param.wall
    total_h = param.wall + param.holder_height

    window_w = param.clock_width - 2 * param.frame_lip
    cavity_y = -outer_d / 2 + param.frame_thickness + inner_d / 2
    front_y = -outer_d / 2 + param.frame_thickness / 2

    result = cq.Workplane("XY").box(
        outer_w, outer_d, total_h, centered=(True, True, False)
    )

    cavity = (
        cq.Workplane("XY", origin=(0, cavity_y, param.wall))
        .rect(inner_w, inner_d)
        .extrude(param.holder_height + 1)
    )

    window = (
        cq.Workplane("XY", origin=(0, front_y, param.wall + param.frame_lip))
        .rect(window_w, param.frame_thickness + 2)
        .extrude(param.holder_height + 1)
    )

    result = result.cut(cavity).cut(window)

    if param.fillet > 0:
        result = result.edges("|Z and (<X or >X)").fillet(param.fillet)

    return result


main = define_app(Param, build)
