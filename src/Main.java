import java.net.*;
import java.io.*;

public class Main {

    public static void main(String[] args) {


        String host = "www.google.com.uy";
        //connectToHost(host,"1.0");
        //connectToHost(host,"1.1");
        connectToHost(host,"2.0");

    }

    private static void  connectToHost(String host, String protocol) {
        try {
            Socket socket = new Socket(host, 80);

            PrintStream out = new PrintStream(socket.getOutputStream());
            BufferedReader in = new BufferedReader(new InputStreamReader(socket.getInputStream()));

            if(protocol.equalsIgnoreCase("1.0")){
                out.println("GET / HTTP/1.0");
            }else{
                out.println("GET / HTTP/1.1");
            }
            out.println("Host: " + host);

            if(protocol.equalsIgnoreCase("2.0")){
                out.println("Connection: Upgrade, HTTP2-Settings");
                out.println( "Upgrade: h2c");
                out.println( "HTTP2-Settings: <base64url encoding of HTTP/2 SETTINGS payload>");
            }
            out.println();
            out.flush();

            int lineCount = 0;
            String [] httpString = null;
            String line = in.readLine();
            //while (line != null) {
            while (lineCount < 1) {
                httpString = line.split(" ");
                System.out.println(host+ " supports " + httpString[0]);
                line = in.readLine();
                lineCount++;
            }

            in.close();
            out.close();
            socket.close();
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

}