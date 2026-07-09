Attribute VB_Name = "Módulo20"
Sub cor()
Attribute cor.VB_ProcData.VB_Invoke_Func = " \n14"
'
' cor Macro
'

'
    With Selection.Interior
        .Pattern = xlSolid
        .PatternColorIndex = xlAutomatic
        .ThemeColor = xlThemeColorDark1
        .TintAndShade = -0.149998474074526
        .PatternTintAndShade = 0
    End With
    Range("D15:L15").Select
End Sub
