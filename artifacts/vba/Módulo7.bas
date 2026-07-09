Attribute VB_Name = "Módulo7"
Sub MP()
Attribute MP.VB_ProcData.VB_Invoke_Func = " \n14"
'
' MP Macro
'

'
    ActiveCell.FormulaR1C1 = "=LEFT(RC[-1],2)"
    Range("C4").Select
End Sub
