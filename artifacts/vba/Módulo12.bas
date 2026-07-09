Attribute VB_Name = "Módulo12"

Public Sub EMAIL()
Dim OutApp As Object
Dim OutMail As Object
Dim texto As String



ActiveWorkbook.Save
    
Set OutApp = CreateObject("Outlook.Application")
Set OutMail = OutApp.CreateItem(0)


    With OutMail
            .To = "romeu.maia@grainproteintech.com" & ";" & "gustavo.goldshmith@grainproteintech.com" & ";" & "Alessandro.PereiradaRosaFilho@grainproteintech.com"
            .CC = ""
            .BCC = ""
            .Subject = "BITIN " & Plan4.Cells(2, 10) '& 'Plan4.Cells(2, 11)
            
            'Texto do corpo do email
            .Body = " Prezados " & "Romeu e Gustavo" & vbCrLf & _
                    " Segue BITin para cadastro/liberação"
                                                             
            .Attachments.Add ActiveWorkbook.FullName

            .Display   'Utilize Send para enviar o email sem abrir o Outlook
            '.Send
        End With
                          
On Error GoTo 0

'Caixa de mensagem de confimação
    Dim resposta As Integer
    resposta = MsgBox("E-mail gerado, deseja fechar o workbook?", vbQuestion + vbYesNo, "Confirmação de Envio")
    
    If resposta = vbYes Then
        
        Set OutMail = Nothing
        Set OutApp = Nothing
        ' O usuário indica que o e-mail foi enviado
        ActiveWorkbook.Close SaveChanges:=False
    End If




'fim da caixa de mensagem

Set OutMail = Nothing
Set OutApp = Nothing


     
End Sub


Private Sub Worksheet_Change(ByVal Target As Range)

On Error GoTo Sair

    If Target.Column = 10 And Target.Row = 2 And Target.Value <> "" Then
        Range("H" & "4").Value = VBA.Date
    End If
    
Sair:
    
End Sub


