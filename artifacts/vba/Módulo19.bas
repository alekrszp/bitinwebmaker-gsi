Attribute VB_Name = "Módulo19"
'..............................................................................................................
'Function que retorna o nome do usuário de rede logado
Function UsuarioRede() As String
    Dim GetUserN
    Dim ObjNetwork
    Set ObjNetwork = CreateObject("WScript.Network")
    GetUserN = ObjNetwork.UserName
    UsuarioRede = GetUserN
    
    Planilha1.Cells(2, 30) = GetUserN ' Preenche o usuário.
    
End Function
