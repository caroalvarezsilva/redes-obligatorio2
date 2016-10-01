import java.net.*;
import java.io.*;

public class Main {

    public static void main(String[] args) {

        try{

            String host = "www.twitter.com";
            //String host = "www.metroflog.com";

            Socket socket = new Socket( host, 443);

            PrintStream out = new PrintStream( socket.getOutputStream() );
            BufferedReader in = new BufferedReader( new InputStreamReader( socket.getInputStream() ) );

            out.println("GET / HTTP/1.1");
            out.println("Host: " + host);
            out.println("Connection: Upgrade, HTTP2-Settings");
            out.println( "Upgrade: h2c");
            out.println( "HTTP2-Settings: <base64url encoding of HTTP/2 SETTINGS payload>");

            out.println();
            out.flush();

            String line = in.readLine();
            while( line != null ){
                int count = 0;
                //while (count < 2) {
                System.out.println( line );
                line = in.readLine();
                //count ++;
                //count ++;
            }

            in.close();
            out.close();
            socket.close();
        }
        catch( Exception e ) {
            e.printStackTrace();
        }
    }
}
