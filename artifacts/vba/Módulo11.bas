Attribute VB_Name = "Módulo11"
Sub clear_winshuttle()
Attribute clear_winshuttle.VB_Description = "Limpa o template do winshuttle"
Attribute clear_winshuttle.VB_ProcData.VB_Invoke_Func = " \n14"
'
' clear_winshuttle Macro
' Limpa o template do winshuttle
'

'
    Rows("3:3").Select
    Range(Selection, Selection.End(xlDown)).Select
    Range(Selection, Selection.End(xlDown)).Select
    Selection.ClearContents
    With Selection.Interior
        .Pattern = xlNone
        .TintAndShade = 0
        .PatternTintAndShade = 0
    End With
    Range("A3").Select
End Sub
