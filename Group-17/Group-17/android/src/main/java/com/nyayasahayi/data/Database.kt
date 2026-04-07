package com.nyayasahayi.data

import androidx.room.*

@Entity(tableName = "cases", indices = [Index(value = ["cnr_number"], unique = true)])
data class LocalCase(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    @ColumnInfo(name = "cnr_number") val cnrNumber: String,
    @ColumnInfo(name = "next_date") val nextDate: String?,
    @ColumnInfo(name = "status") val status: String?,
    @ColumnInfo(name = "history_json") val historyJson: String, // Storing complex object as JSON string
    @ColumnInfo(name = "last_updated_at") val lastUpdatedAt: String
)

@Entity(tableName = "clients", indices = [Index(value = ["phone_number"], unique = true)])
data class LocalClient(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    @ColumnInfo(name = "name") val name: String,
    @ColumnInfo(name = "phone_number") val phoneNumber: String,
    @ColumnInfo(name = "email") val email: String?,
    @ColumnInfo(name = "notes") val notes: String?
)

@Entity(
    tableName = "client_case_map",
    foreignKeys = [
        ForeignKey(entity = LocalClient::class, parentColumns = ["id"], childColumns = ["client_id"], onDelete = ForeignKey.CASCADE),
        ForeignKey(entity = LocalCase::class, parentColumns = ["id"], childColumns = ["case_id"], onDelete = ForeignKey.CASCADE)
    ],
    indices = [Index("client_id"), Index("case_id")]
)
data class ClientCaseMap(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    @ColumnInfo(name = "client_id") val clientId: Long,
    @ColumnInfo(name = "case_id") val caseId: Long,
    @ColumnInfo(name = "role") val role: String // e.g. Petitioner, Respondent
)

@Dao
interface AppDao {
    // Client Queries
    @Query("SELECT * FROM clients WHERE phone_number = :phoneNumber LIMIT 1")
    suspend fun getClientByPhone(phoneNumber: String): LocalClient?

    @Query("SELECT * FROM clients")
    suspend fun getAllClients(): List<LocalClient>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertClient(client: LocalClient): Long

    // Case Queries
    @Query("SELECT * FROM cases WHERE cnr_number = :cnr LIMIT 1")
    suspend fun getCaseByCnr(cnr: String): LocalCase?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertCase(caseItem: LocalCase): Long

    // Mapping Queries
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertClientCaseMap(map: ClientCaseMap)

    // Helper to get cases for a client
    @Transaction
    @Query("""
        SELECT cases.* FROM cases 
        INNER JOIN client_case_map ON cases.id = client_case_map.case_id 
        WHERE client_case_map.client_id = :clientId
    """)
    suspend fun getCasesForClient(clientId: Long): List<LocalCase>

    // Helper to get clients for a case
    @Transaction
    @Query("""
        SELECT clients.* FROM clients
        INNER JOIN client_case_map ON clients.id = client_case_map.client_id
        WHERE client_case_map.case_id = :caseId
    """)
    suspend fun getClientsForCase(caseId: Long): List<LocalClient>
}

@Database(entities = [LocalClient::class, LocalCase::class, ClientCaseMap::class], version = 1)
abstract class AppDatabase : RoomDatabase() {
    abstract fun appDao(): AppDao

    companion object {
        @Volatile
        private var INSTANCE: AppDatabase? = null

        fun getDatabase(context: android.content.Context): AppDatabase {
            return INSTANCE ?: synchronized(this) {
                val instance = Room.databaseBuilder(
                    context.applicationContext,
                    AppDatabase::class.java,
                    "nyayasahayi_db"
                ).build()
                INSTANCE = instance
                instance
            }
        }
    }
}
