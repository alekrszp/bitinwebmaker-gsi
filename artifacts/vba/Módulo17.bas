Attribute VB_Name = "Módulo17"
Sub Limpeza()
Attribute Limpeza.VB_ProcData.VB_Invoke_Func = " \n14"
'
' Limpeza Macro
'

'
    ActiveWindow.SmallScroll Down:=-9
    Range("J2:L2").Select
    Selection.ClearContents
    Range("H3:L3").Select
    Selection.ClearContents
    Range("H4:L4").Select
    Selection.ClearContents
    Range("D3:E3").Select
    Selection.ClearContents
    Range("D4:E4").Select
    Selection.ClearContents
    Range("D8:L26").Select
    Selection.ClearContents
    Range("C9").Select
    Selection.AutoFill Destination:=Range("C9:C30"), Type:=xlFillDefault
    Range("C9:C30").Select
    'Selection.AutoFill Destination:=Range("C9:C30"), Type:=xlFillDefault
    'Range("C9:C30").Select
    Range("N18:S30").Select
    Selection.ClearContents
    Range("A33:U10000").Select
    Selection.ClearContents
    Selection.Font.Bold = False
    Selection.Font.Bold = True
    Selection.Font.Bold = False
    With Selection.Font
        .ThemeColor = xlThemeColorLight1
        .TintAndShade = 0
    End With
    With Selection.Interior
        .Pattern = xlNone
        .TintAndShade = 0
        .PatternTintAndShade = 0
    End With
    Range("B33:L10000").Select
    Selection.RowHeight = 27
    
    Range("A33:A1000").Interior.Color = vbBlack
    Range("M33:U1000").Interior.Color = vbBlack
End Sub
