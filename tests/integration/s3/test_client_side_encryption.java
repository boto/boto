import py4j.GatewayServer;
import com.amazonaws.services.s3.AmazonS3EncryptionClient;
import com.amazonaws.util.Base64;
import javax.crypto.SecretKey;
import javax.crypto.spec.SecretKeySpec;
import com.amazonaws.services.s3.model.EncryptionMaterials;
import com.amazonaws.auth.BasicAWSCredentials;
import org.apache.commons.io.IOUtils;
import java.nio.charset.StandardCharsets;
import com.amazonaws.services.s3.model.ObjectMetadata;
import com.amazonaws.services.s3.model.S3Object;
import java.io.FileInputStream;

public class BotoS3Gateway {

    public AmazonS3EncryptionClient getClient(String accessKey, String secretKey, String base64EncryptionKey) throws Exception {
        SecretKey encryptionKey = new SecretKeySpec(Base64.decode(base64EncryptionKey), "AES");
        EncryptionMaterials encryptionMaterials = new EncryptionMaterials(encryptionKey);

        BasicAWSCredentials credentials = new BasicAWSCredentials(accessKey, secretKey);
        AmazonS3EncryptionClient s3 = new AmazonS3EncryptionClient(credentials, encryptionMaterials);

        return s3;
    }

    public void putString(String accessKey, String secretKey, String base64EncryptionKey, String bucketName, String key, String content) throws Exception {
        AmazonS3EncryptionClient s3 = getClient(accessKey, secretKey, base64EncryptionKey);
        s3.putObject(bucketName, key, IOUtils.toInputStream(content, StandardCharsets.UTF_8.name()), new ObjectMetadata());
    }

    public void putFile(String accessKey, String secretKey, String base64EncryptionKey, String bucketName, String key, String filename) throws Exception {
        AmazonS3EncryptionClient s3 = getClient(accessKey, secretKey, base64EncryptionKey);
        FileInputStream fileInputStream = new FileInputStream(filename);
        s3.putObject(bucketName, key, fileInputStream, new ObjectMetadata());
        fileInputStream.close();
    }

    public String getString(String accessKey, String secretKey, String base64EncryptionKey, String bucketName, String key) throws Exception {
        AmazonS3EncryptionClient s3 = getClient(accessKey, secretKey, base64EncryptionKey);
        S3Object obj = s3.getObject(bucketName, key);
        return IOUtils.toString(obj.getObjectContent(), StandardCharsets.UTF_8.name());
    }

    public static void main(String[] args) {
        System.out.println("Starting gateway...");
        GatewayServer gatewayServer = new GatewayServer(new BotoS3Gateway());
        gatewayServer.start();
    }
}
